function suggestNames() {
    var sequence = $("#id_sequence").val();
    if (!sequence) {
        alert("Sequence is empty. Please enter a sequence to get suggestions.");
    } else {
        var btn = document.querySelector('[data-suggest-names-url]');
        var url = btn ? btn.dataset.suggestNamesUrl : '/ajax/suggestNames';
        $.ajax({
            url: url,
            type: "POST",
            data: {
                'sequence': sequence,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
            },
            success: function (data) {
                $("#suggestedNames").html(data);
            },
        });
    }
}

function searchOpen() {
    var search = $('#id_taxonomy').val();
    $.ajax({
        url: '/search.json',
        data: { search: search },
        dataType: 'json',
        success: function(data) {
            $('#id_taxonomy').autocomplete({ source: data });
        }
    });
}
