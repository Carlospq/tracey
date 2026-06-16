import os, subprocess, pyhmmer

from apps.home.models import Motifs, Verifymotifs, Domaingroups, Domains, Methods
from utils.motifPredictor.updateSnareMotifs import countGaps
from apps.templates.menus.query_sequences_full import menu, get_keys_recursively as _gkr

# ── SNARE-specific per-sequence limits ───────────────────────────────────────

# All domaingroup names under the SNAPbc subtree (SNAP.b/SNAP.c and their leaves)
_SNAPBC_KEYS = frozenset(['SNAPbc'] + _gkr(menu['SNARE']['SNARE']['SNAPbc']))

# Hard caps: max active motifs of this DB domain per sequence
_DOMAIN_LIMITS = {'Habc': 1, 'Longin': 1}
_SNARE_MAX_NONSNAP = 1   # Qa / Qb / Qc / R
_SNARE_MAX_SNAP    = 2   # SNAPbc (SNAP25 has two SNAP domains)

# Habc and Longin are mutually exclusive on the same sequence
_MUTUAL_EXCLUSION = {'Longin': 'Habc', 'Habc': 'Longin'}

# Minimum hit length (aa) per domaingroup; shorter hits are discarded.
_LONGIN_DG_KEYS = frozenset(['Longin'] + _gkr(menu['SNARE']['Longin']))
_SNARE_DG_KEYS = frozenset(['SNARE'] + _gkr(menu['SNARE']['SNARE']))
_HABC_DG_KEYS = frozenset(['SNARE'] + _gkr(menu['SNARE']['Habc']))

_MIN_HIT_LENGTH = {dg: 75 for dg in _LONGIN_DG_KEYS | _HABC_DG_KEYS}
_MIN_HIT_LENGTH.update({dg: 45 for dg in _SNARE_DG_KEYS})

# Fallback by domain name — catches domaingroup name mismatches or new sub-types.
_MIN_DOMAIN_HIT_LENGTH = {'Longin': 50}


def _overlaps(s1, e1, s2, e2):
    """True if the closed intervals [s1,e1] and [s2,e2] share at least one position."""
    return s1 <= e2 and s2 <= e1


def _is_snapbc(dg_name):
    return dg_name in _SNAPBC_KEYS


def _effective_domain_name(m):
    """Resolve the conceptual domain name for a Motifs instance.

    Old Longin motifs may have been stored under domain 'SNARE' (before a
    dedicated Longin domain row existed).  Use the domaingroupname as ground
    truth: any group whose name is in _LONGIN_DG_KEYS or starts with 'longin'
    is treated as domain 'Longin' regardless of the DB domain FK.
    """
    dg_name = m.domaingroup.domaingroupname
    if dg_name in _LONGIN_DG_KEYS or dg_name.lower().startswith('longin'):
        return 'Longin'
    return m.domaingroup.domain.domainname


def _min_len_for_existing(m):
    """Return the minimum allowed length for an existing motif, or None."""
    dg_name = m.domaingroup.domaingroupname
    return (_MIN_HIT_LENGTH.get(dg_name)
            or _MIN_DOMAIN_HIT_LENGTH.get(_effective_domain_name(m)))


def _check_limit(sequence, hit_dg, replacing=None, also_exclude=None):
    """
    Returns True if adding a motif with *hit_dg* to *sequence* is within limits.

    *replacing*     – existing Motifs object being swapped out; excluded from count.
    *also_exclude*  – set of motif_ids already logically removed (e.g. REMOVE-SHORT
                      in dry-run mode where the DB delete hasn't happened yet).
    """
    domain_name = hit_dg.domain.domainname
    exclude_ids = set()
    if replacing:
        exclude_ids.add(replacing.motif_id)
    if also_exclude:
        exclude_ids.update(also_exclude)

    all_existing = list(sequence.motifs_set.select_related('domaingroup__domain').all())

    # Habc ↔ Longin mutual exclusion — use effective domain name, not DB domain_id
    excluded_partner = _MUTUAL_EXCLUSION.get(domain_name)
    if excluded_partner and any(
        _effective_domain_name(m) == excluded_partner and m.motif_id not in exclude_ids
        for m in all_existing
    ):
        return False

    # Count existing motifs of the same effective domain (robust against old DB domain rows)
    existing = [
        m for m in all_existing
        if _effective_domain_name(m) == domain_name
        and m.motif_id not in exclude_ids
    ]

    if domain_name in _DOMAIN_LIMITS:
        return len(existing) < _DOMAIN_LIMITS[domain_name]

    if domain_name == 'SNARE':
        if _is_snapbc(hit_dg.domaingroupname):
            snap_count = sum(1 for m in existing if _is_snapbc(m.domaingroup.domaingroupname))
            return snap_count < _SNARE_MAX_SNAP
        else:
            nonsnap_count = sum(1 for m in existing if not _is_snapbc(m.domaingroup.domaingroupname))
            return nonsnap_count < _SNARE_MAX_NONSNAP

    return True


def reScanMotifs(sequences, hmm_keys, evalue=1e-10, dry_run=False):
    """
    Re-scans sequences against a set of HMMs and updates Motifs/Verifymotifs.

    For each hit found:
      - If it overlaps a same-domain motif and improves the score → replace it.
      - If it overlaps only different-domain motifs → add without touching them.
      - If it has no overlap → add.
    Replacements and additions are blocked when per-domain limits are reached.

    Args:
        sequences:  iterable of Sequences ORM objects to scan.
        hmm_keys:   list of HMM names (without .hmm) from the menu dict.
        evalue:     E-value cutoff passed to hmmscan (default 1e-10).
        dry_run:    if True, print planned actions without writing to DB.
    """
    hmm_keys_set = set(hmm_keys)

    # Collect HMM files from all utils/hmmModels/ subfolders
    hmmList = []
    for folder in os.listdir('utils/hmmModels'):
        folder_path = os.path.join('utils/hmmModels', folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if fname.endswith('.hmm') and fname[:-4] in hmm_keys_set:
                hmmList.append(os.path.join(folder_path, fname))

    if not hmmList:
        print("No HMM files found for keys: %s" % list(hmm_keys))
        return

    tmpHMMdb = "utils/motifPredictor/tmpHMMdb.hmmDb"
    with open(tmpHMMdb, "w") as f:
        for hmm_file in hmmList:
            f.write(open(hmm_file).read())
    subprocess.call("hmmpress -f %s" % tmpHMMdb, shell=True,
                    stdout=open(os.devnull, 'wb'))

    suffix = " [DRY RUN]" if dry_run else ""
    print("Scanning %d sequences against %d HMMs%s" % (len(sequences), len(hmmList), suffix))

    for n, sequence in enumerate(sequences, 1):
        print(f'{n}/{len(sequences)}', sequence)

        if sequence.sequencestatus != 'live':
            print("\t [SKIP] status=%s" % sequence.sequencestatus)
            continue

        seq_clean = sequence.sequence.strip().replace("-", "").replace("+", "")
        if not seq_clean:
            continue

        with pyhmmer.plan7.HMMFile(tmpHMMdb) as hmm_file:
            alphabet = pyhmmer.easel.Alphabet.amino()
            proteins = [pyhmmer.easel.TextSequence(
                name=b"Query", sequence=seq_clean).digitize(alphabet)]
            all_hits = list(pyhmmer.hmmer.hmmscan(proteins, hmm_file, E=evalue, F1=1, F2=1, F3=1))

        # Build hits dict keyed by HMM name, keeping best (lowest) pvalue per HMM
        hits_d = {}
        for hits in all_hits:
            for h in hits:
                h_name = h.name.decode()
                for d in h.domains:
                    if h_name in hits_d and d.pvalue > hits_d[h_name]['pvalue']:
                        continue
                    alignment_str = str(d.alignment)
                    if "RF\n" in alignment_str:
                        dg_name = alignment_str.split("RF\n")[1].split()[0]
                    else:
                        dg_name = alignment_str.split("\n")[0].split()[0]
                    try:
                        dg = Domaingroups.objects.select_related('domain').get(domaingroupname=dg_name)
                    except Domaingroups.DoesNotExist:
                        continue
                    hits_d[h_name] = {
                        'evalue':   format(d.pvalue, '.1E'),
                        'pvalue':   d.pvalue,
                        'env_from': d.env_from,
                        'env_to':   d.env_to,
                        'alignment': d.alignment,
                        'dg':       dg,
                        'motif':    dg.domain.domainname,
                    }

        # Remove existing motifs that violate minimum-length rules.
        # Track their IDs so that subsequent checks treat them as already gone,
        # keeping dry-run output consistent with what the actual run would do.
        short_removed_ids = set()

        # -- NO NEED TO REMOVED PREVIOUSLY VERIFIED MOTIFS GIVEN ITS LENGTH AND THE FACT THAT THEY WERE VERIFIED --
        # for m in list(sequence.motifs_set.select_related('domaingroup__domain').all()):
        #     m_len = m.stopposition - m.startposition + 1
        #     m_min = _min_len_for_existing(m)
        #     if m_min and m_len < m_min:
        #         print("\t [REMOVE-SHORT] %s len=%daa < %daa (stale)" % (
        #             m.domaingroup.domaingroupname, m_len, m_min))
        #         short_removed_ids.add(m.motif_id)
        #         if not dry_run:
        #             m.delete()

        if not hits_d:
            print("\t [NO HITS]")
            continue

        # Process all hits best-first
        for hit in sorted(hits_d.values(), key=lambda x: x['pvalue']):
            hit_start  = hit['env_from']
            hit_end    = hit['env_to']
            hit_dg     = hit['dg']
            hit_len    = hit_end - hit_start + 1   # +1: env coords are 1-based inclusive

            min_len = (_MIN_HIT_LENGTH.get(hit_dg.domaingroupname)
                       or _MIN_DOMAIN_HIT_LENGTH.get(hit_dg.domain.domainname))
            if min_len and hit_len < min_len:
                print("\t [SKIP-LEN] %s (domain=%s) len=%daa < %daa" % (
                    hit_dg.domaingroupname, hit_dg.domain.domainname, hit_len, min_len))
                continue

            # Re-query so each iteration sees DB changes from previous hits.
            # Exclude short_removed_ids to treat REMOVE-SHORT as already applied.
            current = [
                m for m in sequence.motifs_set.select_related('domaingroup__domain').all()
                if m.motif_id not in short_removed_ids
            ]

            # A new hit may only occupy a region that is either free or held by the
            # same domain (in which case the old motif is replaced). Overlapping
            # with a motif of a *different* domain is always rejected.
            overlapping_other = [
                m for m in current
                if _overlaps(m.startposition, m.stopposition, hit_start, hit_end)
                and _effective_domain_name(m) != hit_dg.domain.domainname
            ]
            if overlapping_other:
                print("\t [SKIP-CONFLICT] %s overlaps %s (pos %d-%d)" % (
                    hit_dg.domaingroupname,
                    overlapping_other[0].domaingroup.domaingroupname,
                    hit_start, hit_end))
                continue

            overlapping_same = [
                m for m in current
                if _overlaps(m.startposition, m.stopposition, hit_start, hit_end)
                and _effective_domain_name(m) == hit_dg.domain.domainname
            ]

            if overlapping_same:
                best_existing = min(overlapping_same, key=lambda m: m.get_evalue())
                # if (hit_dg != best_existing.domaingroup or hit['pvalue'] < best_existing.get_evalue()):
                if hit['pvalue'] < best_existing.get_evalue():
                    if _check_limit(sequence, hit_dg,
                                    replacing=best_existing,
                                    also_exclude=short_removed_ids):
                        print("\t [UPDATE] %s (%.1E) -> %s (%s) len=%daa" % (
                            best_existing.domaingroup.domaingroupname,
                            best_existing.get_evalue(),
                            hit_dg.domaingroupname,
                            hit['evalue'],
                            hit_len))
                        if not dry_run:
                            _replace_motif(sequence, best_existing, hit)
                    else:
                        print("\t [SKIP-LIMIT] %s (domain %s full)" % (
                            hit_dg.domaingroupname, hit_dg.domain.domainname))
                else:
                    print("\t [SKIP] %s (%.1E) unchanged" % (
                        best_existing.domaingroup.domaingroupname,
                        best_existing.get_evalue()))
            else:
                # No overlapping same-domain motif — add without touching other-domain motifs
                if _check_limit(sequence, hit_dg,
                                replacing=None,
                                also_exclude=short_removed_ids):
                    print("\t [NEW] %s  pval=%s  len=%daa" % (
                        hit_dg.domaingroupname, hit['evalue'], hit_len))
                    if not dry_run:
                        _save_motif(sequence, hit)
                else:
                    print("\t [SKIP-LIMIT] %s (domain %s full)" % (
                        hit_dg.domaingroupname, hit_dg.domain.domainname))

        #break


# ── helpers ──────────────────────────────────────────────────────────────────
def _get_or_create_method(dg):
    try:
        return Methods.objects.get(domaingroup_id=dg.domaingroup_id)
    except Methods.DoesNotExist:
        method = Methods(domaingroup_id=dg.domaingroup_id, input='', type='hmm', parameter='')
        method.save()
        return method


def _build_asciioutput(hit):
    return (
        '<asciiOutput>\r\t<consensus>%s</consensus>\r\t<similarity>%s\t</similarity>\r\t'
        '<motif>%s</motif>\r\t<eValue>%s</eValue>\r\t<bitscore>0</bitscore>\r</asciiOutput>'
        % (hit['alignment'].hmm_sequence, hit['alignment'].identity_sequence,
           hit['alignment'].target_sequence, format(hit['pvalue'], '.6E'))
    )


def _save_motif(sequence, hit):
    method = _get_or_create_method(hit['dg'])
    new_motif = Motifs(
        sequence=sequence,
        motifname=hit['motif'],
        startposition=hit['env_from'],
        stopposition=hit['env_to'],
        motifcomments='',
        domaingroup=hit['dg'],
        gaps=countGaps(hit['alignment'].target_sequence),
        active=1,
        method=method,
        motifrank=1000000,
        asciioutput=_build_asciioutput(hit),
        binaryoutput='',
    )
    new_motif.save()


def _replace_motif(sequence, old_motif, best_hit):
    new_verifymotif = Verifymotifs(
        sequence=old_motif.sequence,
        motifname=old_motif.motifname,
        startposition=old_motif.startposition,
        stopposition=old_motif.stopposition,
        verifymotifcomments=old_motif.motifcomments,
        domaingroup=old_motif.domaingroup,
        gaps=old_motif.gaps,
        active=0,
        method=old_motif.method,
        verifymotifrank=old_motif.motifrank,
        asciioutput=old_motif.asciioutput,
        binaryoutput=old_motif.binaryoutput,
    )
    new_verifymotif.save()
    _save_motif(sequence, best_hit)
    old_motif.delete()
