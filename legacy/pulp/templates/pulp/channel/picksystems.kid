<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Pick Systems to ${operation.summary}</title>
</head>
<body>
<h1 class="content-overview">Pick Systems to ${operation.summary}</h1>

<span>You have selected the following packages for an install:</span>
${packageList.display(selectedpackages)}

<br/>
<span>Please select the systems below you wish to install the packages on:</span>
<form action="${operation.url}" method="post" class="tableform" name="form">
    <div id="feed">${systemList.display(subbedsystems)}</div>
    <input type="hidden" name="channel_id" value="${channel.id}"/>
    <input py:for="pv in selectedpackages" type="hidden" name="pvid" value="${pv.id}"/>
    <input type="submit" class="submitbutton" value="${operation.button}"/>
</form>

    
</body>
</html>
