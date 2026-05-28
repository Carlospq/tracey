// Simple 3-letter to 1-letter amino acid map
const THREE_TO_ONE_AA = {
    ALA: 'A', ARG: 'R', ASN: 'N',
    ASP: 'D', CYS: 'C', GLN: 'Q',
    GLU: 'E', GLY: 'G', HIS: 'H',
    ILE: 'I', LEU: 'L', LYS: 'K',
    MET: 'M', PHE: 'F', PRO: 'P',
    SER: 'S', THR: 'T', TRP: 'W',
    TYR: 'Y', VAL: 'V', SEC: 'U',
    PYL: 'O',
};

// Color code for different domains
const domainColors = {
    "SNARE": "orange",
    "Habc": "purple",
    "C2": "red",
    "default": "green"
};

// ---- Global-ish state for sequence & selection ----
let residues = [];
let selectedResidues = new Set();
let lastClickedIndex = null;
let residueIndexByKey = {};
let viewerForSelection = null;
let highlightCartoonRep = null;
let baseCartoonRep = null;
let initialOrientation = null;
let surfaceRep = null;
let sticksRep = null;
let isSpinning = false;
let mouseOverResidueKey = null;
let hoverCartoonRep = null;
const residueSpanByKey = {};

window.update3DSelection = update3DSelection;

function residueKey(chain, resi) {
    return `${chain}:${resi}`;
}

// Read the initial PDB URL from the data attribute set by Django
window.initialPdbUrl = (document.getElementById('container-3d') || {}).dataset && document.getElementById('container-3d').dataset.pdbUrl || '';

document.addEventListener('DOMContentLoaded', () => {
    const initialPdbUrl = (window.initialPdbUrl || '').trim() || null;

    const containerEL = document.getElementById('container-3d');
    if (!containerEL) return;  // viewer not present on this page

    const viewportEl = document.getElementById('viewport-3d');
    const sequenceEl = document.getElementById('sequence-3d');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');

    const dropAreaEl = document.getElementById('pdb-drop-area');
    const fileInput = document.getElementById('pdb-file-input');
    const fileButton = document.getElementById('pdb-file-button');

    let motifsData = {};
    let motifsEl = document.getElementById("data-motifs");

    if (motifsEl) {
        motifsData = JSON.parse(motifsEl.textContent);
    } else {
        motifsData = {};
    }

    // 1) Create viewer instance
    const viewer = createViewer(viewportEl);

    // 2) Setup sequence / selection logic
    setupSequencePanel(viewer, sequenceEl, clearSelectionBtn);

    // 3) Setup file upload (click + input + drag & drop)
    setupFileUpload({
        viewer,
        dropAreaEl,
        fileInput,
        fileButton,
        sequenceEl,
        motifsData,
        onStructureLoaded: () => {
            if (dropAreaEl) {
                dropAreaEl.style.display = 'none';
            }
        }
    });

    // 4) If Django provided an URL, load it on page load
    if (initialPdbUrl) {
        loadStructureFromUrl(viewer, initialPdbUrl, sequenceEl, motifsData)
            .then(() => {
                if (dropAreaEl) {
                    dropAreaEl.style.display = 'none';
                }
            })
            .catch(err => {
                console.error('Error loading initial structure:', err);
            });
        containerEL.classList.add('active');
    }

    setupNglToolbar(viewer);

});

/* ================================
 * Viewer creation / loading
 * ================================ */

function createViewer(containerEl) {
    const stage = new NGL.Stage(containerEl, {backgroundColor: 'white'});

    function handleResize() {
        stage.handleResize();
    }
    window.addEventListener('resize', handleResize, false);
    requestAnimationFrame(handleResize);

    initialOrientation = stage.viewerControls.getOrientation();

    stage.signals.clicked.add(pickingProxy => {
        if (!pickingProxy || !pickingProxy.atom) {
            if (mouseOverResidueKey !== null) {
                mouseOverResidueKey = null;
                updateSequenceHoverHighlight();
                update3DHoverHighlight();
            }
            return;
        }

        const atom = pickingProxy.atom;
        const chain = atom.chainname || atom.chain || '';
        const resi = atom.resno;

        const key = residueKey(chain, resi);
        const index = residueIndexByKey[key];
        if (index == null) {
            return;
        }

        if (selectedResidues.has(key)) {
            selectedResidues.delete(key);
        } else {
            selectedResidues.add(key);
        }
        lastClickedIndex = index;

        updateSequenceHighlighting();
        update3DSelection();
    });

    stage.signals.hovered.add(pickingProxy => {
        if (!pickingProxy || !pickingProxy.atom) {
            if (mouseOverResidueKey !== null) {
                mouseOverResidueKey = null;
                updateSequenceHoverHighlight();
                update3DHoverHighlight();
            }
            return;
        }

        const atom = pickingProxy.atom;
        const chain = atom.chainname || atom.chain || '';
        const resi = atom.resno;
        const key = residueKey(chain, resi);

        if (mouseOverResidueKey === key) {
            return;
        }

        mouseOverResidueKey = key;
        updateSequenceHoverHighlight();
        update3DHoverHighlight();
    });

    return {
        stage,
        currentComponent: null,
        highlightCartoonRep: null,
        motifRepresentations: []
    };
}

function colorMotifs(motifsData) {
    if (!motifsData) return;

    for (const motif of Object.values(motifsData)) {
        if (!motif) continue;

        const { start, end, domain } = motif;
        if (start == null || end == null) continue;

        const s = Number(start);
        const e = Number(end);

        if (Number.isNaN(s) || Number.isNaN(e)) continue;
        for (let resi = s; resi <= e; resi++) {
            const chain = residues[resi-1].chain;
            const key = residueKey(chain, resi);
            selectedResidues.add(key);
        }
    }

    updateSequenceHighlighting();
    update3DSelection();
}

function update3DSelection() {
    if (!highlightCartoonRep) return;

    if (selectedResidues.size === 0) {
        highlightCartoonRep.setSelection("none");
        return;
    }

    const seleParts = [];
    selectedResidues.forEach(key => {
        const [chain, resi] = key.split(":");
        seleParts.push(`${resi}:${chain}`);
    });
    highlightCartoonRep.setSelection(seleParts.join(" OR "));
}

function loadStructureFromUrl(viewer, url, sequenceEl, motifsData) {
    clearViewer(viewer);

    return viewer.stage.loadFile(url, { defaultRepresentation: false })
        .then(comp => {
            viewer.currentComponent = comp;

            baseCartoonRep = comp.addRepresentation("cartoon", {
                color: "blue"
            });
            setupHighlightRepresentations(comp);

            mouseOverResidueKey = null;
            lastClickedIndex = null;

            comp.autoView();
            viewer.stage.handleResize();

            initialOrientation = viewer.stage.viewerControls.getOrientation();

            const residuesArray = extractResiduesFromComponent(comp);
            renderSequence(sequenceEl, residuesArray);
            colorMotifs(motifsData, viewer);
        });
}

function loadStructureFromFile(viewer, file, sequenceEl, motifsData) {
    clearViewer(viewer);

    return viewer.stage.loadFile(file, { defaultRepresentation: false })
        .then(comp => {
            viewer.currentComponent = comp;

            baseCartoonRep = comp.addRepresentation("cartoon", {
                color: "blue"
            });

            highlightCartoonRep = comp.addRepresentation("cartoon", {
                sele: "none",
                color: "orange"
            });
            setupHighlightRepresentations(comp);
            mouseOverResidueKey = null;
            lastClickedIndex = null;

            comp.autoView();
            viewer.stage.handleResize();

            initialOrientation = viewer.stage.viewerControls.getOrientation();

            const residuesArray = extractResiduesFromComponent(comp);
            renderSequence(sequenceEl, residuesArray);
            colorMotifs(motifsData, viewer);
        });
}

function clearViewer(viewer) {
    if (viewer.currentComponent) {
        viewer.currentComponent.removeAllRepresentations();
        viewer.currentComponent.dispose();
        viewer.currentComponent = null;
    }
    hoverCartoonRep = null;
}


/* ================================
 * File upload logic
 * ================================ */

function setupFileUpload({ viewer, dropAreaEl, fileInput, fileButton, onStructureLoaded, sequenceEl, motifsData }) {
    if (fileButton && fileInput) {
        fileButton.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', event => {
            const file = event.target.files[0];
            if (file) {
                handleFileSelected(viewer, file, sequenceEl, onStructureLoaded, motifsData);
            }
            event.target.value = '';
        });
    }

    if (dropAreaEl) {
        setupDragAndDrop(dropAreaEl, file => {
            handleFileSelected(viewer, file, sequenceEl, onStructureLoaded, motifsData);
        });
    }
}

function handleFileSelected(viewer, file, sequenceEl, onStructureLoaded, motifsData) {
    loadStructureFromFile(viewer, file, sequenceEl, motifsData)
        .then(() => {
            if (typeof onStructureLoaded === 'function') {
                onStructureLoaded();
            }
        })
        .catch(err => {
            console.error('Error loading structure from file:', err);
        });

    const motifButtons = document.getElementsByClassName('domain-btn');
    Array.from(motifButtons).forEach(button => {
        button.removeAttribute("hidden");
    });
}

function setupDragAndDrop(dropAreaEl, onFile) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropAreaEl.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropAreaEl.addEventListener(eventName, () => {
            dropAreaEl.classList.add('highlight');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropAreaEl.addEventListener(eventName, () => {
            dropAreaEl.classList.remove('highlight');
        }, false);
    });

    dropAreaEl.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files[0]) {
            onFile(files[0]);
        }
    }, false);
}

function extractResiduesFromComponent(comp) {
    const structure = comp.structure;
    const result = [];
    if (!structure) return result;

    structure.eachResidue(residue => {
        const resname = (residue.resname || '').toUpperCase();
        const aa = THREE_TO_ONE_AA[resname] || 'X';
        const chain = residue.chainname || residue.chain || '';
        const resi = residue.resno;

        result.push({ aa, chain, resi });
    });

    console.log('Extracted residues:', result.length);
    return result;
}

function renderSequence(sequenceEl, residuesArray) {
    residues = residuesArray;
    selectedResidues.clear();
    lastClickedIndex = null;
    residueIndexByKey = {};

    Object.keys(residueSpanByKey).forEach(k => delete residueSpanByKey[k]);
    sequenceEl.innerHTML = '';

    residues.forEach((r, idx) => {
        residueIndexByKey[residueKey(r.chain, r.resi)] = idx;
    });

    createResiduesSpans(sequenceEl, residues);
    updateSequenceHighlighting();
}

function createResiduesSpans(sequenceEl, residues) {
    residues.forEach((r, idx) => {
        const span = document.createElement("span");
        const key = residueKey(r.chain, r.resi);
        residueSpanByKey[key] = span;

        span.textContent = r.aa;
        span.className = "residue";
        span.dataset.chain = r.chain;
        span.dataset.resi = r.resi;
        span.dataset.index = idx;

        span.addEventListener("click", (event) => {
            const key = residueKey(r.chain, r.resi);

            if (event.shiftKey && lastClickedIndex !== null) {
                const start = Math.min(lastClickedIndex, idx);
                const end = Math.max(lastClickedIndex, idx);

                for (let i = start; i <= end; i++) {
                    const rr = residues[i];
                    selectedResidues.add(residueKey(rr.chain, rr.resi));
                }
            } else {
                if (selectedResidues.has(key)) {
                    selectedResidues.delete(key);
                } else {
                    selectedResidues.add(key);
                }
            }

            lastClickedIndex = idx;
            updateSequenceHighlighting();
            update3DSelection();
        });

        span.addEventListener("mouseenter", () => {
            const tooltip = document.getElementById("res-tooltip");
            tooltip.classList.remove("hidden");
            tooltip.className = "res-tooltip";
            tooltip.textContent = `Resi: ${r.aa} Pos: ${idx + 1}`;

            mouseOverResidueKey = key;
            updateSequenceHoverHighlight();
            update3DHoverHighlight();
        });

        span.addEventListener("mouseleave", () => {
            const tooltip = document.getElementById("res-tooltip");
            tooltip.classList.add("hidden");

            if (mouseOverResidueKey === key) {
                mouseOverResidueKey = null;
                updateSequenceHoverHighlight();
                update3DHoverHighlight();
            }
        });

        sequenceEl.appendChild(span);
        if ((idx + 1) % 50 === 0) {
            sequenceEl.appendChild(document.createElement("br"));
        }
    });
}

/* ================================
 * Sequence panel / selection
 * ================================ */

function setupSequencePanel(viewer, sequenceEl, clearSelectionBtn) {
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', () => {
            clearSelection(viewer, sequenceEl);
        });
    }
}

function clearSelection(viewer, sequenceEl) {
    selectedResidues.clear();
    lastClickedIndex = null;
    updateSequenceHighlighting();
    if (typeof window.update3DSelection === "function") {
        window.update3DSelection();
    }
}

function updateSequenceHighlighting() {
    document.querySelectorAll("#sequence-3d .residue").forEach(el => {
        el.classList.remove("selected");
    });

    selectedResidues.forEach(key => {
        const [chain, resiStr] = key.split(":");
        const selector = `#sequence-3d .residue[data-chain="${chain}"][data-resi="${resiStr}"]`;
        const span = document.querySelector(selector);
        if (span) {
            span.classList.add("selected");
        }
    });
}

document.querySelectorAll(".domain-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        if (!residues || residues.length === 0) {
            console.warn("No structure loaded yet");
            return;
        }

        const start = parseInt(btn.dataset.start, 10);
        const end   = parseInt(btn.dataset.end, 10);
        let chain   = btn.dataset.chain;

        if (!chain) {
            chain = residues[0].chain;
        }

        selectedResidues.clear();

        let firstIndex = null;

        residues.forEach((r, idx) => {
            if (r.chain === chain && r.resi >= start && r.resi <= end) {
                const key = residueKey(r.chain, r.resi);
                selectedResidues.add(key);

                if (firstIndex === null) {
                    firstIndex = idx;
                }
            }
        });

        lastClickedIndex = firstIndex;

        updateSequenceHighlighting();
        update3DSelection();

        if (firstIndex !== null) {
            const span = document.querySelector(
                `#sequence-3d .residue[data-chain="${chain}"][data-resi="${start}"]`
            );
            if (span) {
                span.scrollIntoView({ block: "center", behavior: "smooth" });
            }
        }
    });
});

function setupNglToolbar(viewer) {
    document.querySelectorAll(".ngl-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const action = btn.dataset.action;

            if (!viewer.currentComponent) {
                console.warn("No structure loaded");
                return;
            }

            switch (action) {
                case "recenter":
                    recenterView(viewer);
                    break;
                case "reset":
                    resetOrientation(viewer);
                    break;
                case "toggle-cartoon":
                    toggleSticks(viewer);
                    btn.classList.toggle("active");
                    break;
                case "toggle-surface":
                    toggleSurface(viewer);
                    btn.classList.toggle("active");
                    break;
                case "spin":
                    toggleSpin(viewer);
                    btn.classList.toggle("active");
                    break;
                case "image":
                    exportImage(viewer);
                    break;
                default:
                    console.warn("Unknown action:", action);
            }
        });
    });
}

function recenterView(viewer) {
    if (selectedResidues.size > 0) {
        const sele = Array.from(selectedResidues)
            .map(key => {
                const [chain, resi] = key.split(":");
                return `${resi}:${chain}`;
            })
            .join(" OR ");

        viewer.currentComponent.autoView(sele);
    } else {
        viewer.currentComponent.autoView();
    }
}

function resetOrientation(viewer) {
    if (!initialOrientation) return;
    viewer.stage.viewerControls.orient(initialOrientation);

    let motifsData = {};
    let motifsEl = document.getElementById("data-motifs");
    if (motifsEl) {
        motifsData = JSON.parse(motifsEl.textContent);
    }
    colorMotifs(motifsData);
}

function toggleSticks(viewer) {
    if (!sticksRep) {
        sticksRep = viewer.currentComponent.addRepresentation("ball+stick", {
            sele: "protein",
            color: "element"
        });
    } else {
        const visible = sticksRep.getVisibility();
        sticksRep.setVisibility(!visible);
    }
}

function toggleSurface(viewer) {
    if (!surfaceRep) {
        surfaceRep = viewer.currentComponent.addRepresentation("surface", {
            sele: "protein",
            opacity: 0.4,
            color: "grey"
        });
    } else {
        const visible = surfaceRep.getVisibility();
        surfaceRep.setVisibility(!visible);
    }
}

function toggleSpin(viewer) {
    isSpinning = !isSpinning;
    viewer.stage.setSpin(isSpinning);
}

function exportImage(viewer) {
    viewer.stage.makeImage({
        factor: 2,
        antialias: true,
        trim: true,
        transparent: false
    }).then(blob => {
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "structure.png";
        link.click();
        URL.revokeObjectURL(link.href);
    });
}

function setupHighlightRepresentations(comp) {
    highlightCartoonRep = comp.addRepresentation("cartoon", {
        sele: "none",
        color: "orange",
        opacity: 1.0
    });

    hoverCartoonRep = comp.addRepresentation("cartoon", {
        sele: "none",
        color: "red",
        opacity: 1.0
    });
}

function update3DHoverHighlight() {
    if (!hoverCartoonRep) return;

    if (!mouseOverResidueKey) {
        hoverCartoonRep.setSelection("none");
        return;
    }

    const [chain, resi] = mouseOverResidueKey.split(":");
    const center = parseInt(resi, 10);
    if (Number.isNaN(center)) {
        hoverCartoonRep.setSelection("none");
        return;
    }
    const start = Math.max(center - 2, 1);
    const end   = center + 2;

    const sele = `${start}-${end}:${chain}`;
    hoverCartoonRep.setSelection(sele);
}

function updateSequenceHoverHighlight() {
    Object.values(residueSpanByKey).forEach(span => {
        span.classList.remove("residue-hover");
    });

    if (!mouseOverResidueKey) return;

    const span = residueSpanByKey[mouseOverResidueKey];
    if (span) {
        span.classList.add("residue-hover");
    }
}

function copyTextToClipboard(text) {
    navigator.clipboard.writeText(text.replace(/-/g, "").toUpperCase()).then(function() {
        alert('Sequence copied to clipboard');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
}
