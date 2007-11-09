<span py:for="p in summaries" xmlns:py="http://purl.org/kid/ns#">
<div>
	<div><h3>${p.title}</h3>
	   (hide ${p.title} details)
	</div>
	<div id="${p.type_one}-perspective-details" class="float=left;">
		<div class="summary">
			<h4>
				Summary
				<hr />
			</h4>
			<ul>
				<li>
					<strong>I own</strong>
					<a href="#">3 ${p.type_one}(more...)</a>
					<ul>
						<li>
							243 Systems subscribed to ${p.type_one} I own
						</li>
						<li>
							6 administrators / 53 viewers of my ${p.type_one}
						</li>
					</ul>
				</li>
				<li>I administer 3 ${p.type_one}</li>
				<li>I may view 100 ${p.type_one}</li>
			</ul>
			<hr />
			
			<ul py:if="not p.type_two == None">
				<li>
					<strong>I own</strong>
					<a href="#">10 ${p.type_two}(more...)</a>
					<ul>
						<li>
							1458 Systems installed ${p.type_two} that I own
						</li>
						<li>6 ${p.type_one} contain my ${p.type_two}</li>
					</ul>
				</li>
				<li>I administer 1 ${p.type_two}</li>
				<li>I may view 3540 ${p.type_two}s</li>
			</ul>
		</div>
		<div>
			<div class="tasks">
				<h4>Tasks</h4>
				<ul>
					<li>
						<a href="">View ${p.type_one}</a>
					</li>
					<li>
						<a href="">Create a new ${p.type_one}</a>
					</li>
					<li>
						<a href="">
							Grant users(s) access to my ${p.type_one}
						</a>
					</li>
					<li>
						<a href="">Clone ${p.type_one}</a>
					</li>
					<li>
						<a href="">Add new package to ${p.type_one}(s)</a>
					</li>
				</ul>
				<br />
				<hr />
				<br />
			</div>
			<div class="search">
				<h4>Search</h4>
				<ul>
					<li>
						Search for a
						<strong>${p.type_one}:</strong>
						<input type="text" />
						<input type="submit" value="Search" />
					</li>
				</ul>
				<br />
				<ul>
					<li>
						Search for a
						<strong>${p.type_two}:</strong>
						<input type="text" />
						<input type="submit" value="Search" />
					</li>
				</ul>
			</div>
		</div>
	</div>
</div>
</span>