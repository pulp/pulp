<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Channel Details</title>
</head>
<body>
<h1 class="content-overview">Channel Details</h1>


<table>
	<tr><td><strong>Name: </strong></td><td> ${channel.name}</td></tr>
	<tr><td><strong>Display Name: </strong></td><td> ${channel.displayName}</td></tr>
	<tr><td><strong>Description: </strong></td><td> ${channel.description}</td></tr>
</table>
<br/>
<a href="${tg.url('/pulp/channel/edit/' + str(channel.id))}">Edit Details</a> ||
<a href="">Get Content into Channel</a> ||
<a href="">Packages in this Channel</a> ||
<a href="">Systems using this Channel</a> 
<br/>

</body>
</html>
