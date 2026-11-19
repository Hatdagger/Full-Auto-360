/* Minimal in-memory LZX decoder front-end for libmspack's lzxd (Xbox 360 XEX "normal" compression).
   usage: lzxdec <in.lzx> <out.bin> <out_size> <window_size> */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mspack.h"
#include "lzx.h"
typedef struct { unsigned char *buf; size_t len, pos; } memfile;
static struct mspack_file *m_open(struct mspack_system *s, const char *f, int m) { return NULL; }
static void m_close(struct mspack_file *f) {}
static int m_read(struct mspack_file *f, void *b, int n) { memfile *m=(memfile*)f; size_t r=m->len-m->pos; if ((size_t)n<r) r=n; memcpy(b,m->buf+m->pos,r); m->pos+=r; return (int)r; }
static int m_write(struct mspack_file *f, void *b, int n) { memfile *m=(memfile*)f; size_t r=m->len-m->pos; if ((size_t)n<r) r=n; memcpy(m->buf+m->pos,b,r); m->pos+=r; return (int)r; }
static int m_seek(struct mspack_file *f, off_t o, int mode) { return -1; }
static off_t m_tell(struct mspack_file *f) { return (off_t)((memfile*)f)->pos; }
static void m_msg(struct mspack_file *f, const char *fmt, ...) {}
static void *m_alloc(struct mspack_system *s, size_t n) { return malloc(n); }
static void m_free(void *p) { free(p); }
static void m_copy(void *a, void *b, size_t n) { memcpy(b, a, n); }
int main(int argc, char **argv) {
  if (argc < 5) return 2;
  FILE *fi = fopen(argv[1], "rb"); fseek(fi, 0, SEEK_END); long il = ftell(fi); fseek(fi, 0, SEEK_SET);
  memfile in = { malloc(il), (size_t)il, 0 }; fread(in.buf, 1, il, fi); fclose(fi);
  size_t olen = strtoul(argv[3], 0, 0); unsigned ws = strtoul(argv[4], 0, 0);
  memfile out = { calloc(1, olen), olen, 0 };
  int bits = 0; unsigned t = ws; while (t >>= 1) bits++;
  struct mspack_system sys = { m_open, m_close, m_read, m_write, m_seek, m_tell, m_msg, m_alloc, m_free, m_copy, NULL };
  struct lzxd_stream *lz = lzxd_init(&sys, (struct mspack_file*)&in, (struct mspack_file*)&out, bits, 0, 0x8000, (off_t)olen, 0);
  if (!lz) { fprintf(stderr, "lzxd_init failed\n"); return 1; }
  int rc = lzxd_decompress(lz, (off_t)olen);
  lzxd_free(lz);
  FILE *fo = fopen(argv[2], "wb"); fwrite(out.buf, 1, olen, fo); fclose(fo);
  fprintf(stderr, "lzxd rc=%d window_bits=%d out=%zu\n", rc, bits, out.pos);
  return rc;
}
