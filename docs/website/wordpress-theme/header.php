<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" <?php language_attributes(); ?>>

<head profile="http://gmpg.org/xfn/11">
<meta http-equiv="Content-Type" content="<?php bloginfo('html_type'); ?>; charset=<?php bloginfo('charset'); ?>" />

<title><?php bloginfo('name'); ?> <?php if ( is_single() ) { ?> &raquo; Blog Archive <?php } ?> <?php wp_title(); ?></title>

<link rel="stylesheet" href="<?php bloginfo('stylesheet_directory'); ?>/reset.css" type="text/css" media="screen" />
<link rel="stylesheet" href="<?php bloginfo('stylesheet_directory'); ?>/pulp.css" type="text/css" media="screen" />
<link rel="stylesheet" href="<?php bloginfo('stylesheet_directory'); ?>/grid.css" type="text/css" media="screen" />
<link rel="stylesheet" href="<?php bloginfo('stylesheet_url'); ?>" type="text/css" media="screen" />
<!--[if IE]><link rel="stylesheet" href="<?php bloginfo('stylesheet_directory'); ?>/ie.css" type="text/css" media="screen" /><![endif]-->
<link rel="alternate" type="application/rss+xml" title="<?php bloginfo('name'); ?> RSS Feed" href="<?php bloginfo('rss2_url'); ?>" />
<link rel="pingback" href="<?php bloginfo('pingback_url'); ?>" />
<link rel="shortcut icon" href="<?php bloginfo('stylesheet_directory'); ?>/images/favicon.ico" />

  <script type="text/javascript">
  var _gaq = _gaq || [];
    _gaq.push(['_setAccount', 'UA-20330081-1']);
      _gaq.push(['_trackPageview']);

  (function() {
      var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
          ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
              var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
                })();
  </script> 

<?php wp_head(); ?>

</head>

<body>

<div id="background">
<div class="container">

  <div id="header" class="cols_12 alpha omega">
    <a href="http://pulpproject.org">
      <div id="logo">
        <h1 class="invisible">Pulp</h1>
      </div>
    </a>
    <div id="tagline">
      <h2 class="invisible">Developer Blog</h2>
    </div>
    <a href="http://redhat.com">
      <div id="redhat">
        <h3 class="invisible">A Red Hat community project</h3>
      </div>
    </a>
  </div>
  <div class="clear"></div>

<!--
  <div id="nav">
    <?php if ( !function_exists('dynamic_sidebar') || !dynamic_sidebar('Top Navigation') ) : ?>
    <ul>
      <?php wp_list_pages('title_li='); ?>
    </ul>
    <?php endif; ?>
  </div>
-->
