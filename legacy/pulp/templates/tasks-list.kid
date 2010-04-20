<div xmlns:py="http://purl.org/kid/ns#">
    <h3 py:if="len(tg.get_perspective().tasks) > 0">Tasks:</h3>
    <ul>
	    <span py:for="t in tg.get_perspective().tasks">
	        <li py:if="t.is_visible()"><a href="${t.url}">${t.display}</a></li>
	    </span> 
    </ul>
</div>