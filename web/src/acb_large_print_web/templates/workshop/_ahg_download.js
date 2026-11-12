function downloadSkillMarkdown(body) {
  var url = "";
  var link = document.createElement("a");
  try {
    url = URL.createObjectURL(new Blob([body.trim() + "\n"], { type: "text/markdown;charset=utf-8" }));
    link.href = url;
    link.download = "SKILL.md";
    document.body.appendChild(link);
    link.click();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    return true;
  } catch (error) {
    if (url) { URL.revokeObjectURL(url); }
    return false;
  } finally {
    link.remove();
  }
}
