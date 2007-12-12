<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Content Overview</title>
</head>
<body>
<h1 class="content-overview">Content Overview</h1>
<br/>

<h2>
    <img id="feed-img-expand" style="display:none;"
        alt="Expand ..." onclick="togglehide('sources')"
        src="/static/images/arrow-right.png" />
    <img id="feed-img-collapse" alt="Collapse ..."
        onclick="togglehide('sources')" src="/static/images/arrow-down.png" />
    Content Sources
    <div class="context-tools">
        <a href="#">(export CSV)</a>
        <a href="#">(edit)</a>
    </div>
</h2>
<div id="feed">${contentSourceList.display(data)}</div>

<br/>
</body>
</html>
