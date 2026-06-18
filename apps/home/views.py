"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home.utils import (
    get_taxonomy_df,
    get_alphafold_url,
    get_menu,
    get_children,
    get_sequences,
    notEmpty,
    md5,
    md5_from_seq,
)

from apps.home.plots import (
    get_motifsColors,
    build_domain_plot,
    build_domain_plot_from_PyHammer,
    get_pdb_data,
    getMotifPlot_fromMotif,
    getLayoutPlot,
    getMotifPlot_fromPyhammer,
)

from apps.home.views_query import (
    index,
    pages,
    QueryView,
    load_taxonomy_rank,
    load_species,
    proteinlayoutToDomaingroups,
    proteinlayoutToDomains,
    load_domains,
    load_domaingroups_rank1,
    load_sequenceshortnames,
    load_taxonomy_by_shortname,
    load_domaingroups_rank2,
    load_queryverifysequences,
    updateSequenceStatus,
    QuerySequences,
    QuerySequencesResults,
    SequencesResultsTable,
    QuerySequencesFastaFormat,
    QuerySequences3dViewer,
    QuerySequencesDetails,
    DetailsSequencesFastaFormat,
    suggest_aliases,
)

from apps.home.views_motifs import (
    motifScan,
    QueryMotifsView,
    QueryMotifsResultsView,
)

from apps.home.views_verify import (
    is_staff,
    staff_login_required,
    saveVerifyMotifs,
    common_name,
    suggested_names,
    suggestNames,
    QueryInsertView,
    QueryVerifyMenuView,
    parseNCBIblastpSTDOUT,
    QueryVerifyBlastView,
    QueryVerifyView,
    autocompleteModel,
)

from apps.home.views_trees import (
    TreesView,
    plotTrees,
)

from apps.home.views_admin import (
    features,
    update_taxonomy,
    update_sequences,
    rescan_motifs,
    update_tree,
    read_update_taxonomy_results,
    read_update_sequences_results,
    upload_sequences,
    download_file,
    download_hmm_zip,
)

from django.http import HttpResponse


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /captcha/",
        "Allow: /",
        "",
        "Sitemap: https://tracey.unil.ch/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
