// ==UserScript==
// @name         Bing Related Search → Send Random (Multi-layout Support)
// @namespace    http://tampermonkey.net/
// @version      1.3
// @description  Collect related searches from different Bing layouts, pick random, send to API, show status
// @match        https://www.bing.com/search?*
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  function createStatusBox() {
    let box = document.createElement("div");
    box.id = "relatedStatusBox";
    box.style.position = "fixed";
    box.style.bottom = "20px";
    box.style.left = "20px"; // bottom-left
    box.style.padding = "10px 15px";
    box.style.background = "#f9f9f9";
    box.style.border = "1px solid #0078d7";
    box.style.borderRadius = "5px";
    box.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
    box.style.fontFamily = "Arial, sans-serif";
    box.style.fontSize = "14px";
    box.style.color = "#333";
    box.style.zIndex = "9999";
    box.innerHTML = "⏳ Waiting for related searches...";
    document.body.appendChild(box);
    return box;
  }

  function getAllRelated() {
    let selectors = [
      ".richrsrailsuggestion_text", // sidebar
      ".suggestion_text", // bottom block
      ".b_suggestionText", // inline block
    ];

    let results = [];
    selectors.forEach((sel) => {
      let nodes = document.querySelectorAll(sel);
      nodes.forEach((n) => {
        let text = n.innerText.trim();
        if (text && !results.includes(text)) {
          results.push(text);
        }
      });
    });

    return results;
  }

  function sendRandomRelated() {
    let box = document.getElementById("relatedStatusBox") || createStatusBox();
    let related = getAllRelated();

    if (related.length === 0) {
      box.innerHTML = "⚠️ No related searches found.";
      return;
    }

    let randomKeyword = related[Math.floor(Math.random() * related.length)];
    box.innerHTML = `📤 Sending: <b>${randomKeyword}</b> ...`;

    let formData = new URLSearchParams();
    formData.append("keywords", randomKeyword);

    fetch("https://bing-search.onrender.com/add_keywords", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    })
      .then((res) => res.json().catch(() => ({})))
      .then((data) => {
        box.innerHTML = `✅ Sent: <b>${randomKeyword}</b>`;
        console.log("✅ Sent successfully:", data);
      })
      .catch((err) => {
        box.innerHTML = `❌ Error sending: <b>${randomKeyword}</b>`;
        console.error("❌ Error sending keyword:", err);
      });
  }

  window.addEventListener("load", () => {
    // wait a bit longer in case Bing loads results dynamically
    setTimeout(sendRandomRelated, 2500);
  });
})();
