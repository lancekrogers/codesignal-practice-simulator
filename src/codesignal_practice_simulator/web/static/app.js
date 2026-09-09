(function () {
  "use strict";

  const fragment = window.location.hash.slice(1);
  const token = new URLSearchParams(fragment).get("token");
  if (token) {
    sessionStorage.setItem("simulator-token", token);
    window.history.replaceState(null, "", window.location.pathname);
  }

  const status = document.getElementById("status");
  const request = async (path) => {
    const response = await fetch(path, {
      headers: { "X-Simulator-Token": sessionStorage.getItem("simulator-token") || "" }
    });
    return response.json();
  };

  request("/api/bootstrap")
    .then((document) => {
      if (!document.ok) throw new Error(document.error.message);
      const assessment = document.data.assessment;
      status.textContent = `${assessment.display_name} is ready.`;
    })
    .catch(() => {
      status.textContent = "This local simulator link is unavailable.";
    });
}());
