<?php // Do not delete these lines
	if (!empty($_SERVER['SCRIPT_FILENAME']) && 'comments.php' == basename($_SERVER['SCRIPT_FILENAME']))
		die ('Please do not load this page directly. Thanks!');

	if (!empty($post->post_password)) { // if there's a password
		if ($_COOKIE['wp-postpass_' . COOKIEHASH] != $post->post_password) {  // and it doesn't match the cookie
			?>

			<p class="nocomments">This post is password protected. Enter the password to view comments.</p>

			<?php
			return;
		}
	}

	/* This variable is for alternating comment background */
	$oddcomment = 'class="alt" ';
?>

<!-- You can start editing here. -->
<div id="comments">

<?php if ($comments) : ?>

	<h3><?php comments_number('No Comments', 'One Comment', '% Comments' );?> on &#8220;<?php the_title(); ?>&#8221;</h3>

	<ol class="commentlist">

	<?php $count_pings = 1; foreach ($comments as $comment) : ?>

		<li <?php echo $oddcomment; ?>id="comment-<?php comment_ID() ?>">
			<div style="float:left;padding-right:5px;"><?php echo get_avatar( $comment, 26 ); ?></div>
			<span><?php echo $count_pings; $count_pings++; ?></span>
			<cite><?php comment_author_link() ?>&nbsp;said at <?php comment_time() ?> on <?php comment_date('F jS, Y') ?>:</cite>
			<?php comment_text() ?>
			<?php if ($comment->comment_approved == '0') : ?>
			<p><b>Your comment is awaiting moderation.</b></p>
			<?php endif; ?>
		</li>

	<?php
		/* Changes every other comment to a different class */
		$oddcomment = ( empty( $oddcomment ) ) ? 'class="alt" ' : '';
	?>

	<?php endforeach; /* end for each comment */ ?>

	</ol>

 <?php else : // this is displayed if there are no comments so far ?>

	<?php if ('open' == $post->comment_status) : ?>
		<!-- If comments are open, but there are no comments. -->

	 <?php else : // comments are closed ?>
		<!-- If comments are closed. -->
		<p class="nocomments">Comments are closed.</p>

	<?php endif; ?>
<?php endif; ?>


<?php if ('open' == $post->comment_status) : ?>

<hr/>
<br/>
<h3 class="center blue">Leave a Reply</h3>

<?php if ( get_option('comment_registration') && !$user_ID ) : ?>
<p>You must be <a href="<?php echo get_option('siteurl'); ?>/wp-login.php?redirect_to=<?php echo urlencode(get_permalink()); ?>">logged in</a> to post a comment.</p>
<?php else : ?>

<form action="<?php echo get_option('siteurl'); ?>/wp-comments-post.php" method="post" id="commentform">

<ul class="formlist">

<?php if ( $user_ID ) : ?>

<p>Logged in as <a href="<?php echo get_option('siteurl'); ?>/wp-admin/profile.php"><?php echo $user_identity; ?></a>. <a href="<?php echo get_option('siteurl'); ?>/wp-login.php?action=logout" title="Log out of this account">Log out &raquo;</a></p>


<?php else : ?>

<li><input type="text" name="author" id="author" value="Name <?php if ($req) echo "(required)"; ?>" size="22" tabindex="1" <?php if ($req) echo "aria-required='true'"; ?> onblur="if(this.value.length == 0) this.value='Name <?php if ($req) echo "(required)"; ?>';" onclick="if(this.value == 'Name <?php if ($req) echo "(required)"; ?>') this.value='';" /></li>

<li><input type="text" name="email" id="email" value="Mail (will not be published) <?php if ($req) echo "(required)"; ?>" size="22" tabindex="2" <?php if ($req) echo "aria-required='true'"; ?> onblur="if(this.value.length == 0) this.value='Mail (will not be published) <?php if ($req) echo "(required)"; ?>';" onclick="if(this.value == 'Mail (will not be published) <?php if ($req) echo "(required)"; ?>') this.value='';" /></li>

<li><input type="text" name="url" id="url" value="Website" size="22" tabindex="3" onblur="if(this.value.length == 0) this.value='Website';" onclick="if(this.value == 'Website') this.value='';" /></li>

<?php endif; ?>

<!--<p><small><strong>XHTML:</strong> You can use these tags: <code><?php echo allowed_tags(); ?></code></small></p>-->

<li><textarea name="comment" id="comment" cols="70%" rows="10" tabindex="4" value="Enter comment here."></textarea></li>

<li class="submitbutton"><input name="submit" type="submit" id="submit" tabindex="5" value="Submit Comment" /></li>
<input type="hidden" name="comment_post_ID" value="<?php echo $id; ?>" />

<?php do_action('comment_form', $post->ID); ?>

</ul>

</form>

<?php endif; // If registration required and not logged in ?>

<?php endif; // if you delete this the sky will fall on your head ?>

</div>
