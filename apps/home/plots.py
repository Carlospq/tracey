import io
import base64
import colorsys
import urllib.parse
import requests
import xml.etree.ElementTree as ET

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from dna_features_viewer import GraphicFeature, GraphicRecord
from django.utils.safestring import mark_safe

from .models import *
from .utils import get_alphafold_url

matplotlib.use('agg')


def get_motifsColors():
    N = len(Domains.objects.all())
    HSV_tuples = [(x * 1.0 / N, 0.5, 0.5) for x in range(N)]
    RGB_tuples = map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples)
    motifColors = {}
    for domain, color in zip(Domains.objects.all(), RGB_tuples):
        motifColors[domain.domainname] = color
    return motifColors


def build_domain_plot(protein_length, domains, eval=None):
    fig = go.Figure()

    fig.add_shape(
        type="rect",
        x0=0,
        x1=protein_length,
        y0=0.45,
        y1=0.55,
        fillcolor="#e0e0e0",
        line=dict(color="black")
    )

    for dom in domains:
        domEval = None
        if not eval:
            tags = {}
            data = ET.fromstring(dom.asciioutput)
            for x in data:
                tags[x.tag] = x.text
            domEval = float(tags["eValue"])
        else:
            domEval = eval

        start = dom.get_real_startposition()
        end = dom.get_real_stopposition()
        label = dom.domaingroup.domain.domainname + " - " + dom.domaingroup.domaingroupname
        motifColors = get_motifsColors()
        domainname = dom.domaingroup.domain.domainname
        color = 'rgb'+str(motifColors[domainname]) if domainname in motifColors else "#cccccc"
        text = (f"{label}<br>Start: {start}<br>End: {end}<br>Length: {end - start + 1} aa<br>E-value: {domEval}" if domEval else
                f"{label}<br>Start: {start}<br>End: {end}<br>Length: {end - start + 1} aa")

        fig.add_shape(
            type="rect",
            x0=start,
            x1=end,
            y0=0.3,
            y1=0.7,
            fillcolor=color,
            line=dict(color="black")
        )

        xs = list(range(start, end + 1))
        ys = [0.5] * len(xs)
        tooltip_color = "rgb(242, 240, 249)"
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            marker=dict(size=1, opacity=0),
            hoverinfo="text",
            text=[f"{text}" for x in xs],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
            hoverlabel=dict(
                bgcolor=tooltip_color,
                bordercolor="black",
                font=dict(color="black")
            )
        ))

        res_per_char = protein_length * 0.003
        label_required_width = len(label) * res_per_char

        if end - start >= label_required_width:
            fig.add_annotation(
                x=(start + end) / 2,
                y=(0.2 + 0.8) / 2,
                text=label,
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                font=dict(color="white", size=12),
                bgcolor="rgba(0,0,0,0)",
                borderpad=0
            )

    fig.update_layout(
        height=155,
        autosize=True,
        xaxis=dict(range=[-5, protein_length + 5], showgrid=False),
        yaxis=dict(visible=False, range=[0, 1], domain=[0.10, 0.90]),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=2, b=10),
        showlegend=False,
    )

    return mark_safe(fig.to_html(include_plotlyjs='cdn', full_html=False))


def build_domain_plot_from_PyHammer(protein_length, hit, evalcutoff=0):
    fig = go.Figure()

    fig.add_shape(
        type="rect",
        x0=0,
        x1=protein_length,
        y0=0.45,
        y1=0.55,
        fillcolor="#e0e0e0",
        line=dict(color="black")
    )

    for d in hit.domains:
        if d.pvalue >= evalcutoff:
            continue

        start = d.alignment.target_from - 1
        end = d.alignment.target_to
        label = str(d.alignment).split("\n")[0].split()[0] if str(d.alignment).split("\n")[0].split()[-1] not in ["RF", "SC"] else str(d.alignment).split("\n")[1].split()[0]
        domEval = str(format(d.pvalue, '.1E'))
        motifColors = get_motifsColors()
        domainname = Domaingroups.objects.get(domaingroupname=label).domain.domainname
        color = 'rgb' + str(motifColors[domainname]) if domainname in motifColors else "#cccccc"

        label += " (%s)" % (domEval) if domEval else ""
        text = (f"{domainname} -  {label}<br>Start: {start}<br>End: {end}<br>Length: {end - start + 1} aa<br>E-value: {domEval}" if domEval else
                f"{domainname} -  {label}<br>Start: {start}<br>End: {end}<br>Length: {end - start + 1} aa<br>")

        fig.add_shape(
            type="rect",
            x0=start,
            x1=end,
            y0=0.3,
            y1=0.7,
            fillcolor=color,
            line=dict(color="black")
        )

        xs = list(range(start, end + 1))
        ys = [0.5] * len(xs)
        tooltip_color = 'rgb(242,240,249)'
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            marker=dict(size=1, opacity=0),
            hoverinfo="text",
            text=[f"{text}" for x in xs],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
            hoverlabel=dict(
                bgcolor=tooltip_color,
                bordercolor="black",
                font=dict(color="black")
            )
        ))

        res_per_char = protein_length * 0.003
        label_required_width = len(label) * res_per_char

        if end - start >= label_required_width:
            fig.add_annotation(
                x=(start + end) / 2,
                y=(0.2 + 0.8) / 2,
                text=label,
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                font=dict(color="white", size=12),
                bgcolor="rgba(0,0,0,0)",
                borderpad=0
            )

    fig.update_layout(
        height=155,
        autosize=True,
        xaxis=dict(range=[-5, protein_length + 5], showgrid=False),
        yaxis=dict(visible=False, range=[0, 1], domain=[0.10, 0.90]),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=2, b=10),
        showlegend=False,
    )

    return mark_safe(fig.to_html(include_plotlyjs='cdn', full_html=False))


def get_pdb_data(sequence):
    AA3_TO_1 = {
        "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D",
        "CYS": "C", "GLN": "Q", "GLU": "E", "GLY": "G",
        "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
        "MET": "M", "PHE": "F", "PRO": "P", "SER": "S",
        "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    }

    pdb_url = get_alphafold_url(sequence)
    if not pdb_url:
        return {}

    try:
        resp = requests.get(pdb_url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {}

    pdb_text = resp.text
    residues = []
    seen = set()

    for line in pdb_text.splitlines():
        if not line.startswith("ATOM"):
            continue
        atom_name = line[12:16].strip()
        if atom_name != "CA":
            continue
        parts = line.split()
        if len(parts) < 19:
            continue
        resname3 = parts[17]
        chain = parts[18] or "_"
        resi = int(parts[8])
        key = (chain, resi)
        if key in seen:
            continue
        seen.add(key)
        aa = AA3_TO_1.get(resname3, "X")
        residues.append({"chain": chain, "resi": resi, "aa": aa})

    return {"pdb_url": pdb_url, "residues": residues}


def getMotifPlot_fromMotif(start, end, length, label):
    motifColors = get_motifsColors()
    domainname = Domaingroups.objects.get(domaingroupname=label).domain.domainname
    buf = io.BytesIO()
    fig, ax = plt.subplots(nrows=1, figsize=(20, 1.5), sharex=True)
    features = [
        GraphicFeature(
            start=start, end=end, label=label,
            color=motifColors[domainname] if domainname in motifColors else "#ffcccc"
        ),
    ]
    record = GraphicRecord(sequence_length=length, features=features)
    record.plot(ax=ax)
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return uri


def getLayoutPlot(sequence):
    motifColors = get_motifsColors()
    buf = io.BytesIO()
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(20, 2), sharex=True, gridspec_kw={"height_ratios": [5, 1]})
    features = [
        GraphicFeature(
            start=m.get_real_startposition(), end=m.get_real_stopposition(),
            label=m.motifname + " | " + m.domaingroup.domaingroupname,
            color=motifColors[m.domaingroup.domain.domainname] if m.domaingroup.domain.domainname in motifColors else "#ffcccc",
            linewidth=0.75,
            fontdict={'fontsize': 8}
        )
        for m in sequence.motifs_set.all()
    ]
    record = GraphicRecord(sequence_length=len(sequence.sequence), features=features)
    record.plot(ax=ax1, with_ruler=False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    plt.yticks([])
    fig.tight_layout(pad=5)
    fig.subplots_adjust(left=0.01, bottom=0.3, right=0.99, top=1, wspace=0.05, hspace=0.1)
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return uri


def getMotifPlot_fromPyhammer(hit, sequence, evalcutoff=1e-10):
    buf = io.BytesIO()
    fig, ax = plt.subplots(nrows=1, figsize=(15, 1.5), sharex=True)
    motifColors = get_motifsColors()
    features = [
        GraphicFeature(
            start=d.alignment.target_from - 1, end=d.alignment.target_to,
            label=(
                str(d.alignment).split("\n")[0].split()[0]
                if str(d.alignment).split("\n")[0].split()[-1] not in ["RF", "SC"]
                else str(d.alignment).split("\n")[1].split()[0]
            ) + " (%s)" % (format(d.pvalue, '.1E')),
            color="#ffcccc"
        )
        for d in hit.domains if d.pvalue < evalcutoff
    ]
    record = GraphicRecord(sequence_length=len(sequence), features=features)
    record.plot(ax=ax)
    fig.tight_layout()
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    plt.close(fig)
    return uri
