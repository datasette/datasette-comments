A very small demo application to try out `datasette-comments`.

To deploy, I build it with:

```bash
docker build ../ -f Dockerfile -t datasette-comments
```

Then to deploy:

```bash
fly deploy --image datasette-comments --local-only
```
