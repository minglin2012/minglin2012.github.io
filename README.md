# Wangyajun Blog

> 王亚君的技术博客 — 记录、分享、共同成长。

[https://blog.junjun.tech](https://blog.junjun.tech)

---

基于 [Hux Blog](https://github.com/Huxpro/huxpro.github.io) 主题构建，托管于 GitHub Pages。

### 本地运行

需要 [Ruby](https://www.ruby-lang.org/) 和 [Bundler](https://bundler.io/)：

```sh
bundle install
bundle exec jekyll serve
```

浏览器访问 `localhost:4000`。

### 发布文章

```sh
rake post title="文章标题" subtitle="副标题"
```

在生成的 Markdown 文件中撰写内容，提交推送后 GitHub Actions 自动部署。

### License

Apache License 2.0. Copyright (c) 2015-present Huxpro

Hux Blog 基于 [Clean Blog Jekyll Theme (MIT License)](https://github.com/BlackrockDigital/startbootstrap-clean-blog-jekyll/)  
Copyright (c) 2013-2016 Blackrock Digital LLC.
