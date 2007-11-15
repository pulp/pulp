<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <link rel="shortcut icon" href="static/images/favico-ponies.png" type="image/vnd.microsoft.icon" />
    <link rel="icon" href="static/images/favico-ponies.png" type="image/vnd.microsoft.icon" /> 
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <meta py:replace="item[:]"/>
    <style type="text/css">
        #pageLogin
        {
            font-size: 10px;
            font-family: verdana;
            text-align: right;
        }
    </style>
    <style type="text/css" media="screen">
@import "${tg.url('/static/css/master.css')}";
</style>
    <script type="text/javascript">
 
    function SwitchTheme(theme) {
      document.body.id = theme;
    }

    </script>
</head>
<body id="${tg.get_perspective()}" py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">
    <div py:if="tg.config('identity.on') and not defined('logging_in')" id="pageLogin">
        <span py:if="tg.identity.anonymous">
            <a href="${tg.url('/login')}">Login</a>
        </span>
        <span py:if="not tg.identity.anonymous">
            <span>Welcome</span> ${tg.identity.user.display_name}
            <a href="${tg.url('/logout')}">Logout</a>
        </span>
    </div>
    
    <div id="head">
<h1><a href="/">Buster</a></h1>

<div id="searchbar">
    <select>
      <option>Systems</option>
      <option>Software</option>
      <option>Users</option>
      <option>Events</option>
    </select>
    <input class="text" type="text" value="Type search terms here."/>
    <input class="button" type="submit" value="Search!"/><br/>
    <a href="#"><div id="pageLogin">Advanced Search...</div></a>
  </div>
</div>

<!--  Nav Bar -->
<!-- see nav.kid -->
${tg_NavBar.display()}

<div id="switcher" style="float: right; margin-right: 24px; margin-bottom: 12px;">
Theme Picker  
<!--  ${tg_GlobalWidget.display()}  -->
<select style="margin-left: 10px;" name="themeSwitcher">
  <option onClick="SwitchTheme('');">Boring</option>
  <option onClick="SwitchTheme('ponies');">Ponies!1</option>
  <option onClick="SwitchTheme('planes');">PLANES!</option>
  <option onClick="SwitchTheme('bonbons');">mmm... yummy bonbons</option>
  <option onClick="SwitchTheme('snakes');">snakes!!</option>
</select>
</div>

<div id="content" style="clear: both;">


<!-- SIDEBAR START -->
<!--  TODO: Replace with one component -->
${tg_SideBar.display()}
<!-- 
<span py:replace="tg.if_path('/', 'pulp.templates.overview-sidebar')" />
<span py:replace="tg.if_path('/users', 'pulp.templates.users-sidebar')" />
<span py:replace="tg.if_path('/groups', 'pulp.templates.groups-sidebar')" />
<span py:replace="tg.if_path('/search', 'pulp.templates.groups-sidebar')" />
 -->

<!-- END SIDEBAR -->

<div id="details">

    <!--START MAIN CONTENT-->
    
    <div id="main_content">
    <div id="status_block" class="flash" py:if="value_of('tg_flash', None)" py:content="tg_flash"></div>

    <div py:replace="[item.text]+item[:]"/>
    <!-- End of main_content -->
    </div>
</div>

</div>
 

 

</body>

</html>
