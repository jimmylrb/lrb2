/* 二伯杀毒官网 — 交互脚本 */
(function(){
  'use strict';

  /* ---------- 移动端导航 ---------- */
  var navToggle = document.getElementById('navToggle');
  var navLinks = document.querySelector('.nav-links');
  if (navToggle) {
    navToggle.addEventListener('click', function(){
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach(function(a){
      a.addEventListener('click', function(){ navLinks.classList.remove('open'); });
    });
  }

  /* ---------- 导航滚动阴影 ---------- */
  var nav = document.getElementById('nav');
  window.addEventListener('scroll', function(){
    if (window.scrollY > 10) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  });

  /* ---------- 数字滚动动画 ---------- */
  function animateCount(el){
    var target = parseInt(el.getAttribute('data-target'), 10) || 0;
    var duration = 1400;
    var start = null;
    function step(ts){
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3); /* easeOutCubic */
      el.textContent = Math.round(target * eased).toLocaleString('en-US');
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if (en.isIntersecting){
        en.target.querySelectorAll('.count').forEach(animateCount);
        io.unobserve(en.target);
      }
    });
  }, { threshold: 0.4 });

  document.querySelectorAll('.hero-stats, .db-panel, .mini-cards').forEach(function(scope){
    io.observe(scope);
  });

  /* ---------- 界面模拟：侧边栏切换 ---------- */
  var sideItems = document.querySelectorAll('.side-item');
  var pages = document.querySelectorAll('.app-main .page');
  sideItems.forEach(function(btn){
    btn.addEventListener('click', function(){
      sideItems.forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      var target = 'page-' + btn.getAttribute('data-page');
      pages.forEach(function(p){ p.classList.toggle('active', p.id === target); });
    });
  });

  /* ---------- 扫描进度条动画（进入视口时） ---------- */
  var barObserver = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      if (en.isIntersecting){
        var i = en.target.querySelector('.scan-bar i');
        if (i) i.style.width = '68%';
        barObserver.unobserve(en.target);
      }
    });
  }, { threshold: 0.3 });
  var scanWrap = document.querySelector('.scan-bar-wrap');
  if (scanWrap){
    scanWrap.querySelector('.scan-bar i').style.width = '0%';
    barObserver.observe(scanWrap);
  }

  /* ---------- 终端打字机效果 ---------- */
  var lines = document.querySelectorAll('.terminal-body p');
  var tIdx = 0;
  lines.forEach(function(p){
    var full = p.textContent;
    p.setAttribute('data-full', full);
    p.textContent = '';
  });
  function typeNext(){
    if (tIdx >= lines.length) return;
    var p = lines[tIdx];
    var full = p.getAttribute('data-full');
    var i = 0;
    var timer = setInterval(function(){
      p.textContent = full.slice(0, ++i);
      if (i >= full.length){ clearInterval(timer); tIdx++; setTimeout(typeNext, 120); }
    }, 14);
  }
  setTimeout(typeNext, 600);

})();
