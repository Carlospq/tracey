import sys

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.home.models import Sequences, Taxonomies
from apps.templates.menus.query_sequences_full import menu, get_keys_recursively
from utils.motifPredictor.reScanMotifs import reScanMotifs


_NOT_FOUND = object()


def _find_menu_node(d, key):
    """Return the sub-dict for *key* anywhere in the nested menu, or _NOT_FOUND."""
    if key in d:
        return d[key]
    for v in d.values():
        if isinstance(v, dict):
            result = _find_menu_node(v, key)
            if result is not _NOT_FOUND:
                return result
    return _NOT_FOUND


class Command(BaseCommand):

    help = ('Re-scan sequences against HMMs and update Motifs/Verifymotifs. '
            'Requires --hmm or --family to specify which HMMs to use.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--motif-filter', type=str, required=False,
            help='Filter sequences to those that already have a motif for this domain '
                 'in the DB (e.g. SNARE, C2). Use to avoid scanning unrelated sequences.')
        parser.add_argument(
            '--evalue', type=float, default=1e-5,
            help='E-value cutoff passed to hmmscan (default 1e-5).')
        parser.add_argument(
            '--hmm', type=str, required=False,
            help='Specific HMM key from the menu (e.g. Longin.I, Longin). '
                 'Includes the key itself plus all its children in the menu.')
        parser.add_argument(
            '--family', type=str, required=False,
            help='Top-level family key in the menu (e.g. SNARE, C2). '
                 'Uses all HMMs under that family.')
        parser.add_argument(
            '--species', type=str, required=False,
            help='Filter by species shortname or scientific name (e.g. HoSa).')
        parser.add_argument(
            '--onlyActive', action='store_true', default=False,
            help='Process only sequences with sequencestatus="live".')
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Print planned actions without writing to the database.')

    def handle(self, *args, **options):

        # ── Resolve HMM keys ───────────────────────────────────────────────
        if options['hmm']:
            node = _find_menu_node(menu, options['hmm'])
            if node is _NOT_FOUND:
                sys.exit("HMM key '%s' not found in menu." % options['hmm'])
            hmm_keys = [options['hmm']] + get_keys_recursively(node)

        elif options['family']:
            if options['family'] not in menu:
                sys.exit("Family '%s' not found in menu. Available: %s"
                         % (options['family'], list(menu.keys())))
            hmm_keys = get_keys_recursively(menu[options['family']])

        else:
            sys.exit("Specify at least --hmm <key> or --family <key> to select HMMs.")

        self.stdout.write("HMM keys (%d): %s" % (len(hmm_keys), hmm_keys))

        # ── Resolve sequences ──────────────────────────────────────────────
        sequences = Sequences.objects.all()

        if options['onlyActive']:
            sequences = sequences.filter(sequencestatus='live')

        if options['species']:
            root_taxa = Taxonomies.objects.filter(
                Q(taxonomyshortname=options['species']) |
                Q(scientificname=options['species'])
            )
            if not root_taxa.exists():
                sys.exit("Species '%s' not found in TRACEY." % options['species'])

            # BFS downward: expand to all descendant taxonomies
            tax_ids = set(root_taxa.values_list('taxonomy_id', flat=True))
            frontier = list(tax_ids)
            while frontier:
                children = list(
                    Taxonomies.objects.filter(taxonomyparent_id__in=frontier)
                    .values_list('taxonomy_id', flat=True)
                )
                new_ids = [c for c in children if c not in tax_ids]
                tax_ids.update(new_ids)
                frontier = new_ids

            self.stdout.write("Taxon '%s' expands to %d taxonomy IDs." % (options['species'], len(tax_ids)))
            sequences = sequences.filter(taxonomy_id__in=tax_ids)

        if options['motif_filter']:
            sequences = sequences.filter(
                motifs__domaingroup__domain__domainname=options['motif_filter']
            ).distinct()

        if not sequences.exists():
            self.stdout.write("No sequences match the given filters.")
            return

        self.stdout.write("Sequences to scan: %d" % sequences.count())
        reScanMotifs(list(sequences), hmm_keys, evalue=options['evalue'], dry_run=options['dry_run'])

