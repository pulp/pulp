<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head>
<title>Hello</title>
<link media="all" href="css/style.css" type="text/css" charset="utf-8" rel="stylesheet" />
</head>
<body>


<div id="head" class="ponies">
  <h1><a href="/">Buster</a></h1>
  <div id="searchbar">
    <select>
      <option>Systems</option>
      <option>Software</option>
      <option>Users</option>
      <option>Events</option>
    </select>
    <input class="text" type="text" value="Type search terms here."/>
    <input class="button" type="submit" value="Search!"/>
  </div>
</div>

<div id="navbar">
  <ul>
    <li><a href="#">Overview</a></li>
    <li class="active"><a href="#">Users</a></li>
    <li><a href="#">Groups</a></li>
    <li><a href="#">Resources</a></li>
    <li><a href="#">Policy</a></li>
    <li><a href="#">Search</a></li>
  </ul>
</div>

<div id="content">

<!-- SIDEBAR START -->
    <div id="sidebar">
    
<h2>About Me:</h2>
  <ul>
  <li><a href="#">Update my password</a></li>
  <li><a href="#">Update my contact information</a></li>
  </ul>

<h2>About Users:</h2>
  <ul>
  <li><a href="#">Add a new user</a></li>
  <li><a href="#">Other users on my team</a></li>
  <li><a href="#">Other users in my department</a></li>
  <li><a href="#">Other users in my office</a></li>
  </ul>

<hr />

<h3>Find a User:</h3>
  <input class="text" type="text" value="Type search terms here."/>
  <input class="button" type="submit" value="Search!"/>

<hr />

  <ul id="navbar-secondary">
  <li class="active"><a href="#">Browse Users</a></li>
  <li><a href="#">Browse User Groups</a></li>
  <li><a href="#">Search for Users</a></li>
  <li><a href="#">Manage User Policies</a></li>
  </ul>
</div>
<!-- END SIDEBAR -->



    <div id="main_content">
    <div id="status_block" class="flash" py:if="value_of('tg_flash', None)" py:content="tg_flash"></div>

    <div py:replace="[item.text]+item[:]"/>

    <!-- End of main_content -->
    </div>

</div>

</body>
</html>


