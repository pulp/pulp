<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"
	xmlns:py="http://purl.org/kid/ns#" py:extends="'master.kid'">
	<head>
		<meta content="text/html; charset=utf-8"
			http-equiv="Content-Type" py:replace="''" />
		<title>Overview</title>
	</head>
	<script>
function togglehide(id){ 
    div = document.getElementById(id)
    collapse = document.getElementById(id + "-img-collapse")
    expand = document.getElementById(id + "-img-expand")
    if (div.style.display != 'none') {
        div.style.display= 'none';
        collapse.style.display= 'none';
        expand.style.display= '';
    }
    else {
        div.style.display= '';
        collapse.style.display= '';
        expand.style.display= 'none';
        
    }
}
</script>
	<body>
		<div id="pageheading">
			<img src="static/images/star.png" />
			<strong>My Overview</strong>
		</div>
		<br />

		<!--  INFO FEED -->
		<h2>
			<img id="feed-img-expand" style="display:none;"
				alt="Expand ..." onclick="togglehide('feed')"
				src="static/images/arrow-right.png" />
			<img id="feed-img-collapse" alt="Collapse ..."
				onclick="togglehide('feed')" src="static/images/arrow-down.png" />
			Info Feed
			<div class="context-tools">
				<a href="#">(export CSV)</a>
				<a href="#">(edit)</a>
			</div>
		</h2>
		<div id="feed">${infoFeed.display(data)}</div>
		<a href="#">(view more events)</a>
		<a href="#">
			rss
			<img src="static/images/feed-icon-14x14.png" />
		</a>
		<br />
		<br />
		<br />


		<!--  MY PERSPECTIVES -->
		<h2>
			<img id="perspectives-img-expand" style="display:none;"
				alt="Expand ..." onclick="togglehide('perspectives')"
				src="static/images/arrow-right.png" />
			<img id="perspectives-img-collapse" alt="Collapse ..."
				onclick="togglehide('perspectives')"
				src="static/images/arrow-down.png" />
			My Perspectives
			<div class="context-tools">
				<a href="#">(export CSV)</a>
				<a href="#">(edit)</a>
			</div>
		</h2>
		<div id="perspectives">
			<h3>Software Content</h3>
			(hide software content details)
			<br />
			<div>
				<div class="summary">
					<h4>Summary<hr/></h4>
					<ul>
					   <li>
							<strong>I own</strong>
							<a href="#">3 software channels(more...)</a>
							<ul>
							  <li>243 Systems subscribed to channels I own</li>
							  <li>6 administrators / 53 viewers of my channels</li>
							</ul>
					   </li>
					   <li>I administer </li>
					   <li>I may view </li>
					</ul>
					<hr/>
                    <ul>
                       <li>
                            <strong>I own</strong>
                            <a href="#">10 software packages(more...)</a>
                            <ul>
                              <li>1458 Systems installed packages that I own</li>
                              <li>6 software channels contain my packages</li>
                            </ul>
                       </li>
                       <li>I administer 1 software packages </li>
                       <li>I may view 3540 software packages</li>
                    </ul>
				</div>
				<div>
					<div class="tasks"><h4>Tasks</h4>
					   <ul>
					       <li><a href="">View Channels</a></li>
					       <li><a href="">Create a new software channel</a></li>
					       <li><a href="">Grant users(s) access to my channels</a></li>
					       <li><a href="">Clone software channels</a></li>
					       <li><a href="">Add new package to channel(s)</a></li>
					   </ul>
					   <br/>
					   <hr/>
					   <br/>
					</div>
					<div class="search"><h4>Search</h4>
					   <ul>
					    <li>Search for a <strong>channel:</strong>
					        <input type="text"/><input type="submit" value="Search"/></li>
					   </ul>
					   <br/>
                       <ul> 					        
                        <li>Search for a <strong>package:</strong>
                            <input type="text"/><input type="submit" value="Search"/></li>
                       </ul>
                    </div>
				</div>
			</div>
		</div>
	</body>
</html>
