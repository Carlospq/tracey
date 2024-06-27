import requests, io, subprocess, sys, re, os

from utils.ncbi_taxonomy.TaxonomyUpdater import update_tracey_taxonomies
from datetime import date
from django.core.management.base import BaseCommand
from django.db.models import Q

from bs4 import BeautifulSoup
from apps.home.models import *

taxa = 'superkingdom'

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--taxa", action="store", dest="taxa", default="superkingdom", help="Taxa group to split taxonomies by groups (colors)")

    def handle(self, *args, **options):
        today = date.today()

        update_tracey_taxonomies()