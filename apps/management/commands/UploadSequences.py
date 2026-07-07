from django.core.management.base import BaseCommand

from utils.traceySequenceUploader.uploadSequences import upload_sequences_from_file


class Command(BaseCommand):

    help = 'Parse an uploaded FASTA file, create Sequences entries and re-scan motifs (runs detached from the request that triggered it).'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the FASTA file saved by the upload view.')
        parser.add_argument('--evalue', type=float, default=1e-5, help='E-value cutoff passed to hmmscan (default 1e-5).')
        parser.add_argument('--username', type=str, required=True, help='Username of the staff member who uploaded the file (for changelog).')
        parser.add_argument('--log-file', type=str, required=True, help='Path to write the final HTML result report to.')

    def handle(self, *args, **options):
        upload_sequences_from_file(
            options['file_path'],
            options['evalue'],
            options['username'],
            options['log_file'],
        )
