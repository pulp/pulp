<?php get_header(); ?>

    <div id="content" class="cols_12">
        <div class="cols_7">
	<?php if (have_posts()) : ?>

		<?php while (have_posts()) : the_post(); ?>
                <div class="light-bg region">
		<div class="post">
			<h1 class="orange shadow"><a href="<?php the_permalink() ?>"><?php the_title(); ?></a></h1>
			<small><?php the_time('F jS, Y') ?> by <?php the_author_posts_link(); ?></small>

			<p><?php the_content('Read the rest of this entry &raquo;'); ?></p>

<br/><small>Categories: <?php the_category(', ') ?> <?php the_tags(' | Tags: ', ', ', ''); ?> <?php if ( $user_ID ) : ?> | <?php edit_post_link(); ?> <?php endif; ?>| <?php comments_popup_link('No Comments &#187;', '1 Comment &#187;', '% Comments &#187;'); ?></small>

		</div>
		
		<?php comments_template(); ?>
	        </div>
	
		<?php endwhile; ?>

                <div class="light-bg region">
		<div class="navigation">
			<div class="alignleft"><a href="<?php next_posts_link() ?>">&laquo; Older Entries</a></div>
			<div class="alignright"><a href="<?php previous_posts_link() ?>">Newer Entries &raquo;</a></div>
<br/>
		</div>
                </div>

	<?php else : ?>

		<h2 class="center">Not Found</h2>
		<p class="center">Sorry, but you are looking for something that isn't here.</p>

	<?php endif; ?>

        </div>

        <div class="cols_4_5">
            <?php get_sidebar(); ?>
        </div

    </div>
	
<?php get_footer(); ?>
