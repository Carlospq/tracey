# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),

    # Download  files
    path('download/<str:filename>', views.download_file, name='download_file'),

    # Features
    path('features.html', views.features, name='features'),

    # Query
    path('query', views.QueryView, name='query'),

    # Sequences
    path('query-sequences', views.QuerySequences, name='query-sequences'),
    path('query-sequences-results', views.QuerySequencesResults, name='query-sequences-results'),
    path('query/fastaFormat/', views.QuerySequencesFastaFormat, name='query-sequences-fasta'),
    path('query-sequences/<int:sequence_id>/details/', views.QuerySequencesDetails, name='query-sequences-details'),
    path('details/fastaFormat/<int:sequence_id>/', views.DetailsSequencesFastaFormat, name='details-sequences-fasta'),

    # Trees
    path('trees', views.TreesView, name='trees'),

    # Motifs
    path('query-motifs', views.QueryMotifsView, name='query-motifs'),
    path('query-motifs-results', views.QueryMotifsResultsView, name='query-motifs-results'),

    # Insert
    path('query-insert', views.QueryInsertView, name='query-insert'),

    # Verify
    path('query-verify', views.QueryVerifyMenuView, name='query-verify-menu'),
    path('query-verify/<int:sequence_id>', views.QueryVerifyView, name='query-verify'),
    path('query-verify/traceyBLAST/<str:db>/<int:query_id>', views.QueryVerifyBlastView, name='query-verify-blast'),
    path('search.json', views.autocompleteModel, name='search.json'),

    # Taxonomy update results
    path('update_taxonomy_results', views.read_update_taxonomy_results, name='read_update_taxonomy_results'),

    # Ajax views
    path('ajax/load-taxonomy-rank/', views.load_taxonomy_rank, name='ajax_load_taxonomy_rank'),
    path('ajax/load-domaingroups-rank1/', views.load_domaingroups_rank1, name='ajax_load_domaingroups_rank1'),
    path('ajax/load-domaingroups-rank2/', views.load_domaingroups_rank2, name='ajax_load_domaingroups_rank2'),
    path('ajax/load-species/', views.load_species, name='ajax_load_species'),
    path('ajax/load-sequenceshortnames/', views.load_sequenceshortnames, name='ajax_load_sequenceshortnames'),
    path('ajax/load-queryverifysequences/', views.load_queryverifysequences, name='ajax_load_queryverifysequences'),
    path('ajax/update-taxonomy/', views.update_taxonomy, name='ajax_update_taxonomy'),
    path('ajax/ajax-update-tree/', views.update_tree, name='ajax_update_tree'),
    path('ajax/plot_phylogenetic_tree', views.plotTrees, name="ajax_plot_phylogenetic_tree"),
    path('ajax/updateSequenceStatus', views.updateSequenceStatus, name="ajax_updateSequenceStatus"),
    path('ajax/suggestNames', views.suggestNames, name="ajax_suggestNames"),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),


]
