<!-- SIDEBAR START -->
<div id="sidebar" xmlns:py="http://purl.org/kid/ns#" py:extends="'master.kid'">
    <span py:replace="tg.task_list()"/>
    
    <h2>About Me:</h2>
      <ul>
      <li><a href="#">Update my password / contact info</a></li>
      </ul>
    <hr />
    
    <h3>My Roles:</h3>
      <ul>
        <li><strong>Content Owner <a href="#">(more ...)</a></strong></li>
        <li><strong>System Owner <a href="#">(more ...)</a></strong></li>
      </ul>
    <hr />
    
    <!-- see perspective-summary.kid -->
    <span py:replace="tg.perspective_list()" />
    
</div>
<!-- END SIDEBAR -->