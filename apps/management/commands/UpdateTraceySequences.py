import sys, os

from utils.traceySequenceUpdater.traceySequencesUpdater import updateSequences
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.home.models import *

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--continue", action="store_true", default=False, help="Continue from the last log file")
        parser.add_argument("--force", action="store_true", default=False, help="Force a new complete update of TRACEY sequences")
        parser.add_argument("--onlyActive", action="store_true", default=False, help="Update only active sequences")
        parser.add_argument("--species", type=str, required=False, help="Update sequences for a specific species")
        parser.add_argument("--traceyIds", type=int, nargs='+', required=False, help="Update specific TRACEY ID sequence")


    def handle(self, *args, **options):
        today = date.today()
        sequencesAnalysed = []

        # Check if species is specified and if it exists in TRACEY
        if options['species']:
            try:
                taxonomies = Taxonomies.objects.filter(Q(taxonomyshortname=options['species']) | Q(scientificname=options['species']))
            except Taxonomies.DoesNotExist:
                sys.exit("Species name not found in TRACEY. Please confirm that the given species name is correct.")

            if len(taxonomies) == 0:
                sys.exit("Species name not found in TRACEY. Please confirm that the given species name is correct.")

        # Continue update from last log file
        if options['continue']:
            oldLogs = [x for x in os.listdir('./utils/traceySequenceUpdater') if 'log' in x]
            # If not log files, ask if user wants to start a new complete update
            if len(oldLogs) == 0:
                inputValue = input("There are no old log files in the folder. Do you want to start a new complete update of TRACEY sequences? [y/n]: ")
                if inputValue.lower() == 'y':
                    logFileName = "./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d")
                    logFile = open(logFileName, "w")
                    logFile.write("traceyID\tncbiID\tshortname_old\tshortname_new\tcomment\n")
                else:
                    sys.exit("Update cancelled.")
            # If log files, continue from the last one
            else:
                # print("Checking previous log file...")
                oldDate = ".".join(oldLogs[-1].split('.')[-4:-1])
                logFileNameOld = "./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % oldDate
                logFileName = "./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d")
                os.rename(logFileNameOld, logFileName)
                logFile = open(logFileName, "r")
                sequencesAnalysed = [int(x.split()[0]) for x in logFile.readlines() if x.split()[0].isdigit()]
        # Force a new complete update of TRACEY sequences
        elif options['force']:
            logFileName = "./utils/traceySequenceUpdater/traceySequencesUpdater.%s.log" % today.strftime("%Y.%m.%d")
            logFile = open(logFileName, "w")
            logFile.write("traceyID\tncbiID\tshortname_old\tshortname_new\tcomment\n")
        else:
            sys.exit("Please specify if you want to continue from the last log file or force a new complete update of TRACEY sequences.")
        logFile.close()

        updateSequences(sequencesAnalysed, options['species'], options['traceyIds'], options['onlyActive'])