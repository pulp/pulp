<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Systems using Channel</title>
</head>
<body>
<h1 class="content-overview">Systems using Channel</h1>

<form action="/pulp/channel/systemstochannel" method="post" class="tableform" name="form">
    <div id="feed">${systemList.display(data)}</div>
<input type="hidden" name="channel_id" value="${channel.id}"/>
<input type="submit" class="submitbutton" value="Subscribe systems to channel!"/>
</form>

    
</body>
</html>
