<div xmlns:py="http://purl.org/kid/ns#">
    
  <table>  
    <tr>
        <td>
            <table>
                <tr>
                    <td>
                        &nbsp;
                        <span py:if="not tg.paginate.current_page == 1">
                            <a href="${tg.paginate.get_href(1)}">&lt;&lt;</a>
                            <a href="${tg.paginate.get_href(tg.paginate.current_page-1)}">&lt;</a>
                        </span>
                    </td>
                    <td>
                        <span py:if="tg.paginate.page_count > 1" py:for="page in tg.paginate.pages">
                            <span py:if="page == tg.paginate.current_page" py:replace="page"/>
                            <span py:if="page != tg.paginate.current_page">
                                <a href="${tg.paginate.get_href(page)}">${page}</a>
                            </span>
                        </span>
                    </td>
                    <td>
                        <span py:if="tg.paginate.pages and not tg.paginate.current_page == tg.paginate.page_count">
                            <a href="${tg.paginate.get_href(tg.paginate.current_page+1)}">&gt;</a>
                            <a href="${tg.paginate.get_href(tg.paginate.page_count)}">&gt;&gt;</a>
                        </span>
                        &nbsp;
                    </td>
                    </tr>    
            </table>        
        </td>
    </tr>
    <tr>
        <td>
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
                <a py:if="col.get_option('type', 'Raw') == 'Raw'">
                    ${col.get_field(row)}
                </a>
              </td>
            </tr>
          </table>
        </td>
    </tr>
  </table>
</div>

