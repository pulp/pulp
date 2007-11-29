<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>List Page</title>
</head>
<body>
<form action="save" method="post" name="theform">
${sortableList.display(data)}
<br/>
${newValue.display(_("Input New Value"))} ${save.display(_('Save'))}
</form>
<hr/>

<br/>
<!--p py:content="form.display(submit_text='Add Comment')">Comment form</p-->
</body>
</html>
