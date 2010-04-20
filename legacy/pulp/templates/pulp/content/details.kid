<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Content Source Details</title>
</head>
<body>
<h1 class="content-overview">Content Source Details</h1>


<h2>Details</h2>
<table>
	<tr><td><strong>Name: </strong></td><td> ${source.name}</td></tr>
	<tr><td><strong>Description: </strong></td><td> ${source.description}</td></tr>
	<tr><td><strong>Type: </strong></td><td> ${source.contentSourceType.displayName}</td></tr>
	<tr><td><strong>Url: </strong></td><td> ${source.configuration.properties.entry[0].value.stringValue}</td></tr>
</table>
<br/>
<a href="${tg.url('/pulp/content/edit/' + str(source.id))}">Edit Details</a>
<br/><br/>
<h2>Packages</h2>
<table>
    <tr><td><strong>Count: </strong></td><td> ${packageCount} </td></tr>
    <tr><td><strong>Type: </strong></td><td> RPMs </td></tr>
    <tr><td><strong>Sync status: </strong></td><td> TBD </td></tr>
</table>
<br/>
<a href="${tg.url('/pulp/content/sync/' + str(source.id))}">Sync remote content into source</a>


<!-- a href="">Packages from this Source</a> ||
<a href="">Channels using this Source</a> --> 
<br/>

</body>
</html>
