function render({ model, el }) {
   // Clear container in case of re-render
   el.innerHTML = "";

   const iframe = document.createElement("iframe");
   iframe.style.border = "none";
   iframe.style.width = model.get("width") || "100%";
   iframe.style.height = model.get("height") || "600px";

   el.appendChild(iframe);

   function updateFrame() {
      const html = model.get("html") || "";
      // Use srcdoc so that NVL scripts/styles inside the HTML run correctly
      if (iframe.srcdoc !== html) {
         iframe.srcdoc = html;
      }

      const width = model.get("width");
      const height = model.get("height");
      if (width) iframe.style.width = width;
      if (height) iframe.style.height = height;
   }

   // React to model changes
   model.on("change:html", updateFrame);
   model.on("change:width", updateFrame);
   model.on("change:height", updateFrame);

   // Initial render
   updateFrame();
}

export default { render };
