<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'../../master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Sync Content Source</title>
</head>
<body>

<h2>Sync Content</h2>
Submitting this form will fetch the content from this URL: <strong>${source.url}</strong>
<br/><br/>
${form.display(action=tg.url("/pulp/content/performsync"), value=source)}

<br/>
</body>
</html>
