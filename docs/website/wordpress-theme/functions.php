<?php

if ( function_exists('register_sidebar') )
    register_sidebar(array(
		'name' => 'Sidebar',
        'before_widget' => '<div class="green-bg region sidebar">',
        'after_widget' => '</div>',
        'before_title' => '<h2 class="green">',
        'after_title' => '</h2>',
    ));
	
if ( function_exists('register_sidebar') )
    register_sidebar(array(
        'name' => 'Top Navigation',
        'before_widget' => '',
        'after_widget' => '',
        'before_title' => '',
        'after_title' => '',
    ));

?>
