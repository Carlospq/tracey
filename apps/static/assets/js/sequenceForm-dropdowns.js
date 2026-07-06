function setLoading(el) {
    $(el).html('<option>Loading…</option>').prop('disabled', true);
}

function clearSelect(el) {
    $(el).html('').prop('disabled', false);
}

// Change in ProteinLayout
$("#proteinlayout").change(function () {
    var urldomains = $("#motifForm").attr("data-load-domains-url");
    var proteinlayout = $(this).val();

    setLoading("#domain");
    clearSelect("#domaingroups");
    clearSelect("#domainsubgroups");

    $.ajax({
        url: urldomains,
        data: { 'proteinlayout': proteinlayout },
        success: function (data) {
            $("#domain").html(data).prop('disabled', false);
        }
    });
});

// Change in Domain
$("#domain").change(function () {
    var urldomaingroupsrank1 = $("#motifForm").attr("data-load-domaingroups-rank1-url");
    var urldomaingroupsrank2 = $("#motifForm").attr("data-load-domaingroups-rank2-url");
    var proteinlayout = $("#proteinlayout").val();
    var domainname = $(this).val();

    setLoading("#domaingroups");
    clearSelect("#domainsubgroups");

    $.ajax({
        url: urldomaingroupsrank1,
        data: { 'proteinlayout': proteinlayout, 'domainname': domainname },
        success: function (data) {
            $("#domaingroups").html(data).prop('disabled', false);
        }
    });

    $.ajax({
        url: urldomaingroupsrank2,
        data: { 'domaingroup_rank': '' },
        success: function (data) {
            $("#domainsubgroups").html(data);
        }
    });
});

// Change in Domain (manual motif form)
// manual_domain values are top-level menu keys (same as proteinlayout)
$("#manual_domain").change(function () {
    var urldomaingroupsrank1 = $("#motifForm").attr("data-load-domaingroups-rank1-url");
    var proteinlayout = $(this).val();

    setLoading("#manual_domaingroup");
    clearSelect("#manual_domainsubgroup");

    $.ajax({
        url: urldomaingroupsrank1,
        data: { 'proteinlayout': proteinlayout, 'domainname': '' },
        success: function (data) {
            $("#manual_domaingroup").html(data).prop('disabled', false);
        }
    });
});

// Change in Domain group (manual motif form)
$("#manual_domaingroup").change(function () {
    var urldomaingroupsrank2 = $("#motifForm").attr("data-load-domaingroups-rank2-url");
    var proteinlayout = $("#manual_domain").val();
    var domaingroup_rank = $(this).val();

    setLoading("#manual_domainsubgroup");

    $.ajax({
        url: urldomaingroupsrank2,
        data: { 'proteinlayout': proteinlayout, 'domainname': '', 'domaingroup_rank': domaingroup_rank },
        success: function (data) {
            $("#manual_domainsubgroup").html(data).prop('disabled', false);
        }
    });
});

// Change in Domain group
$("#domaingroups").change(function () {
    var urldomaingroupsrank2 = $("#motifForm").attr("data-load-domaingroups-rank2-url");
    var proteinlayout = $("#proteinlayout").val();
    var domain = $("#domain").val();
    var domaingroup_rank = $(this).val();

    setLoading("#domainsubgroups");

    $.ajax({
        url: urldomaingroupsrank2,
        data: {
            'proteinlayout': proteinlayout,
            'domainname': domain,
            'domaingroup_rank': domaingroup_rank
        },
        success: function (data) {
            $("#domainsubgroups").html(data).prop('disabled', false);
        }
    });
});
