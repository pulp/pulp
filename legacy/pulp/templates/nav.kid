<div id="navbar" xmlns:py="http://purl.org/kid/ns#">
	<ul>
	  <span py:for="t in tabs"> 
	  <li py:if="t.active" class="active">
	    <a href="${t.url}">${t.name}</a>
	  </li>
      <li py:if="not t.active">
        <a href="${t.url}">${t.name}</a>
      </li>
	  </span>
	</ul>
</div>



