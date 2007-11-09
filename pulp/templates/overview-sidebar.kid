<!-- SIDEBAR START -->
<div id="sidebar" xmlns:py="http://purl.org/kid/ns#" py:extends="'master.kid'">
    <h2>About My Overview:</h2>
      <ul>
      <li><a href="#">Add a new perspective</a></li>
      <li><a href="#">Customize my info feed</a></li>
      <li><a href="#">Modify my overview page layout</a></li>
      </ul>
    
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
    <h3>Other Perspectives:</h3>

    <a href="/setperspective?perspective=content">Software Content</a>
        <strong py:if="tg.if_perspective('content')">(current)</strong>
    <br />
    <small>advanced software content management</small>
    <br />
    <a href="/setperspective?perspective=admin">Admin</a>
        <strong py:if="tg.if_perspective('admin')">(current)</strong>
    <br />
    <small>create/manage clusters and their storage</small>
    <br />
    <a href="/setperspective?perspective=middleware">Middleware</a>
        <strong py:if="tg.if_perspective('middleware')">(current)</strong>
    <br />
    <small>manage middleware applications</small>
    <br />
</div>
<!-- END SIDEBAR -->