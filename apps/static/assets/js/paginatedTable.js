$(document).ready(function(){
    $('table.paginated').each(function() {
        var currentPage = 0;
        var numPerPage = $( "#dt-length-0 option:selected" ).text();
        var $table = $(this);
        $table.bind('repaginate', function() {
            $table.find('tbody tr').hide().slice(currentPage * numPerPage, (currentPage + 1) * numPerPage).show();
        });
        $table.trigger('repaginate');
        var numRows = $table.find('tbody tr').length;
        var numPages = Math.ceil(numRows / numPerPage);
        var $pager = $( ".pager" );
        $('<p style="margin-bottom: auto; margin-top: auto; padding-left: 10px">Page: </p>').appendTo($pager);
        for (var page = 0; page < numPages; page++) {
            $('<span class="page-number"></span>').text(page + 1).bind('click', {
                newPage: page
            }, function(event) {
                currentPage = event.data['newPage'];
                $table.trigger('repaginate');
                $(this).addClass('active').siblings().removeClass('active');
            }).appendTo($pager).addClass('clickable');
        }
        //$pager.insertBefore($table.parent()).find('span.page-number:first').addClass('active');
        $pager.appendTo($pager.parent()).find('span.page-number:first').addClass('active');
    });
});