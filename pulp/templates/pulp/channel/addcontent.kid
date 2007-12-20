<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Content Overview</title>
</head>
<body>
<p>By clicking the 'Associate' column below will copy the content from the 
    Content Source into the Channel.  This allows you to easily populate your 
    Channels with the content your systems need.</p>  
<br/>
<h2>Pick your Content Sources to link to the ${channel.displayName} channel</h2>
<form action="/pulp/channel/contenttochannel" method="post" class="tableform" name="form">
    <div id="feed">${channelList.display(data)}</div>
<input type="hidden" name="channel_id" value="${channel.id}"/>
<input type="submit" class="submitbutton" value="Get content into channel!"/>
</form>
<br/>
</body>
</html>
