from django.core.management.base import BaseCommand

from utils.traceySequenceUpdater.updateDomainGroupsWithHMMs import update_domaingroups_with_hmms


class Command(BaseCommand):

    help = ('Sync new utils/hmmModels/*.hmm files into the staff family menu '
            '(apps/templates/menus/query_sequences_full.py), create the matching '
            'Domaingroups rows in the database, and rebuild utils/hmmModels/MOTIFS.hmmDb.')

    def add_arguments(self, parser):
        parser.add_argument('--log-file', type=str, required=False,
                            help='Write the HTML result report here (terminated by DONE_MARKER). '
                                 'Used by the "Update Domaingroups" feature in features.html.')

    def handle(self, *args, **options):
        report = update_domaingroups_with_hmms(options.get('log_file'))
        self.stdout.write(report)
