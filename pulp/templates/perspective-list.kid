<div xmlns:py="http://purl.org/kid/ns#">
    <h3>Other Perspectives:</h3>
    <span py:for="p in tg.get_all_perspectives()">
	    <a href="/setperspective?perspective=${p.name}">${p.name}</a>
	        <strong py:if="tg.if_perspective(p.name)">(current)</strong>
	    <br />
	    <small>${p.description}</small>
	    <br />
    </span>
</div>