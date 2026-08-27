/* Exclusive-accordion fallback.
   Modern browsers group <details name="cases"> natively — only one stays open.
   Older engines ignore the attribute, so enforce the same behaviour by hand. */
(function () {
  if ('name' in HTMLDetailsElement.prototype) return;

  var groups = {};

  Array.prototype.forEach.call(
    document.querySelectorAll('details[name]'),
    function (el) {
      var key = el.getAttribute('name');
      (groups[key] = groups[key] || []).push(el);
    }
  );

  Object.keys(groups).forEach(function (key) {
    groups[key].forEach(function (el) {
      el.addEventListener('toggle', function () {
        if (!el.open) return;
        groups[key].forEach(function (other) {
          if (other !== el) other.open = false;
        });
      });
    });
  });
})();
