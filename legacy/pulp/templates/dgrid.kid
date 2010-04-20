<div xmlns:py="http://purl.org/kid/ns#">

<!-- START PAGINATION CONTROLS -->
<div class="top-toolbar ${name}">
<div class="search-bar">
Search this List:
<input id="dgrid.searchinput" type="text" name="searchstring" />
<button onClick="performSearch();return false;">Search</button>
<script>
    function performSearch() {
        sstring = document.getElementById('dgrid.searchinput').value;
        url = document.URL;
        if (url.indexOf('?') > 0) {
            url = url + '&amp;searchstring=' + sstring;
        }else {
            url = url + '?&amp;searchstring=' + sstring;
        }
        window.location = url;
    }
</script>

</div>
 <div class="pagination">    
  <span py:if="not tg.paginate.current_page == 1">
    <a class="page-back page-control" href="${tg.paginate.get_href(tg.paginate.current_page-1)}">&lt; Back</a>
    <a class="page-first page-control" href="${tg.paginate.get_href(1)}">&lt;&lt; First</a>
  </span>
  <span py:if="tg.paginate.current_page == 1">
    <a class="page-back page-control disabled" href="${tg.paginate.get_href(tg.paginate.current_page-1)}">&lt; Back</a>
    <a class="page-first page-control disabled" href="${tg.paginate.get_href(1)}">&lt;&lt; First</a>
  </span>
                        
  <span py:if="tg.paginate.page_count > 1" py:for="page in tg.paginate.pages">
  <span class="current-page" py:if="page == tg.paginate.current_page" py:replace="page"/>
    <span py:if="page != tg.paginate.current_page">
      <a class="page-number page-control" href="${tg.paginate.get_href(page)}">${page}</a>
    </span>
  </span>

  <span py:if="tg.paginate.pages and not tg.paginate.current_page == tg.paginate.page_count">
    <a class="page-last page-control" href="${tg.paginate.get_href(tg.paginate.page_count)}">Last &gt;&gt;</a>
    <a class="page-next page-control" href="${tg.paginate.get_href(tg.paginate.current_page+1)}">Next &gt;</a>
  </span>
  <span py:if="tg.paginate.current_page == tg.paginate.page_count">
    <a class="page-last page-control disabled" href="${tg.paginate.get_href(tg.paginate.page_count)}">Last &gt;&gt;</a>
    <a class="page-next page-control disabled" href="${tg.paginate.get_href(tg.paginate.current_page+1)}">Next &gt;</a>
  </span>
</div>
&nbsp;
</div>
<!-- END PAGINATION CONTROLS -->

<!-- START DATAGRID / TABLE -->
<table id="${name}" class="grid">
  <thead py:if="columns">
    <th py:for="i, col in enumerate(columns)" class="col_${i}">
        <a py:if="col.get_option('sortable', False) and getattr(tg, 'paginate', False)" 
           href="${tg.paginate.get_href(1, col.name, col.get_option('reverse_order', False))}">${col.title}</a>
         <span py:if="not getattr(tg, 'paginate', False) or not col.get_option('sortable', False)" py:replace="col.title"/> 
     </th>
  </thead>
  <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
    <td py:for="col in columns">
      <!--Val[ ${col.get_field(row)}] name: ${col.name} -->              
      <a py:if="col.get_option('type', False) == 'Text'">
        <input type="text" size="15" name="${col.name}" value="${col.get_field(row)}"/>
      </a>
      <a py:if="col.get_option('type', False) == 'Checkbox'">
        <input type="checkbox" name="${col.name}" value="${col.get_field(row)}"/>
      </a>
      <a py:if="col.get_option('type', False) == 'link'">
      <a href="${col.get_option('href').replace('*id*', row.id)}">${col.get_field(row)}</a>
        </a>
      <a py:if="col.get_option('type', 'Raw') == 'Raw'">${col.get_field(row)}</a>
    </td>        
  </tr>
</table>
<!-- END DATAGRID / TABLE -->

</div>
