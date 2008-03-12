<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"
	xmlns:py="http://purl.org/kid/ns#" py:extends="'master.kid'">
	<head>
		<meta content="text/html; charset=utf-8"
			http-equiv="Content-Type" py:replace="''" />
		<title>Overview</title>
	</head>
	<script src="/static/javascript/util.js"/>
	<body>
		<h1 class="overview">My Overview</h1>

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
        <!-- RENDER PERSPECTIVE WIDGET/TEMPLATE -->	
        ${ps.display()}	
		</div> <!-- End of Perspective -->
	</body>
</html>
