<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Channel Packages</title>
</head>
<body>
<h1 class="content-overview">Channel Packages</h1>

<form action="/pulp/channel/operateonpackages" method="post" class="tableform" name="form">
    <div id="feed">${packageList.display(data)}</div>

<br/>
<input type="hidden" name="channel_id" value="${channel.id}"/>
<select name="operation">
    <option value="installsystem">Install on Systems</option>
    <option value="deletefromsystem">Remove from Systems</option>
    <option value="deletefromchannel">Remove from Channel</option>
</select>
<input type="submit" class="submitbutton" value="Go!"/>
</form>

</body>
</html>
