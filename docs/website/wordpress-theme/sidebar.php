	<?php if ( !function_exists('dynamic_sidebar')
        || !dynamic_sidebar('Sidebar') ) : ?>

		<div class="block">
			<h3>Recent Posts</h3>
				<?php query_posts('showposts=5'); ?>
				<ul>
					<?php while (have_posts()) : the_post(); ?>
					<li><a href="<?php the_permalink() ?>"><?php the_title(); ?></a></li>
					<?php endwhile;?>
				</ul>
		</div>
		
		<div class="block">
			<h3>Archives</h3>
				<ul>
				<?php wp_get_archives('type=monthly'); ?>
				</ul>
		</div>
		
		<div class="block">
			<h3>Categories</h3>
				<ul>
					<?php wp_list_categories('title_li='); ?>
				</ul>
		</div>
		
		<div class="block">
			<?php wp_list_bookmarks('title_before=<h3>&title_after=</h3>&category_before=&category_after='); ?>
		</div>
		
		<div class="block">
			<h3>Meta</h3>
				<ul>
					<?php wp_register(); ?>
					<li><?php wp_loginout(); ?></li>
					<li><a href="<?php bloginfo('rss2_url'); ?>">RSS</a></li>
					<li><a href="<?php bloginfo('comments_rss2_url'); ?>">Comment RSS</a></li>
					<li><a rel="nofollow" href="http://validator.w3.org/check/referer">Valid XHTML</a></li>
					<?php wp_meta(); ?>
				</ul>
		</div>
		
	<?php endif; ?>

<div id="rss-link">
<a href="<?php bloginfo('rss_url'); ?>"><img src="<?php bloginfo('template_url'); ?>/images/rss-icon.jpg"/>Blog Entries RSS</a>
</div>
