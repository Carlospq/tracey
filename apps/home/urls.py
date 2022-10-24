# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),

    # Users
    path('users.html', views.users, name='users'),

    # Query
    path('query', views.QueryView, name='query'),

    # Sequences
    path('query-sequences', views.QuerySequences, name='query-sequences'),
    path('query-sequences-results', views.QuerySequencesResults, name='query-sequences-results'),
    path('query/fastaFormat/', views.QuerySequencesFastaFormat, name='query-sequences-fasta'),
    path('query-sequences/<int:sequence_id>/details/', views.QuerySequencesDetails, name='query-sequences-details'),
    path('details/fastaFormat/<int:sequence_id>/', views.DetailsSequencesFastaFormat, name='details-sequences-fasta'),

    # Motifs
    path('query-motifs', views.QueryMotifsView, name='query-motifs'),
    path('query-motifs-results', views.QueryMotifsResultsView, name='query-motifs-results'),

    # Insert
    path('query-insert', views.QueryInsertView, name='query-insert'),

    # Verify
    path('query-verify', views.QueryVerifyMenuView, name='query-verify-menu'),
    path('query-verify/<int:sequence_id>', views.QueryVerifyView, name='query-verify'),

    # Ajax views
    path('ajax/load-taxonomy-rank/', views.load_taxonomy_rank, name='ajax_load_taxonomy_rank'),
    path('ajax/load-domaingroups-rank1/', views.load_domaingroups_rank1, name='ajax_load_domaingroups_rank1'),
    path('ajax/load-domaingroups-rank2/', views.load_domaingroups_rank2, name='ajax_load_domaingroups_rank2'),
    path('ajax/load-sequenceshortnames/', views.load_sequenceshortnames, name='ajax_load_sequenceshortnames'),
    path('ajax/load-queryverifysequences/', views.load_queryverifysequences, name='ajax_load_queryverifysequences'),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),


]
