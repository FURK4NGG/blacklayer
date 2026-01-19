#include <gtk/gtk.h>
#include <gtk-layer-shell/gtk-layer-shell.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* ---------- default black color ---------- */
static const GdkRGBA DEFAULT_COLOR = { 0.0, 0.0, 0.0, 1.0 };

static GdkPixbufAnimation *anim;
static GdkPixbufAnimationIter *iter;
static int SW, SH;

/* ---------- draw callback ---------- */
static gboolean draw_cb(GtkWidget *w, cairo_t *cr, gpointer data) {

    /* background black */
    cairo_set_source_rgba(
        cr,
        DEFAULT_COLOR.red,
        DEFAULT_COLOR.green,
        DEFAULT_COLOR.blue,
        DEFAULT_COLOR.alpha
    );
    cairo_paint(cr);

    if (!iter)
        return FALSE;

    GdkPixbuf *frame = gdk_pixbuf_animation_iter_get_pixbuf(iter);
    if (!frame)
        return FALSE;

    int RW = gdk_pixbuf_get_width(frame);
    int RH = gdk_pixbuf_get_height(frame);

    double scale_w = (double)SW / RW;
    double scale_h = (double)SH / RH;
    double scale = (scale_w > scale_h) ? scale_w : scale_h;

    int NW = RW * scale;
    int NH = RH * scale;

    int x = (SW - NW) / 2;
    int y = (SH - NH) / 2;

    cairo_save(cr);
    cairo_translate(cr, x, y);
    cairo_scale(cr, scale, scale);
    gdk_cairo_set_source_pixbuf(cr, frame, 0, 0);
    cairo_paint(cr);
    cairo_restore(cr);

    return FALSE;
}

/* ---------- frame timer ---------- */
static gboolean tick_cb(gpointer data) {
    if (!iter)
        return TRUE;

    gdk_pixbuf_animation_iter_advance(iter, NULL);
    gtk_widget_queue_draw(GTK_WIDGET(data));
    return TRUE;
}

/* ---------- monitor id ---------- */
static int get_monitor_id(const char *name) {
    char cmd[256];
    snprintf(cmd, sizeof(cmd),
        "hyprctl -j monitors | jq -r '.[] | select(.name==\"%s\") | .id'", name);

    FILE *fp = popen(cmd, "r");
    if (!fp) return -1;

    int id = -1;
    fscanf(fp, "%d", &id);
    pclose(fp);
    return id;
}

/* ---------- resource ---------- */
static char *get_resource(void) {
    static char line[512];
    char path[512];

    snprintf(path, sizeof(path),
        "%s/.config/blacklayer/blacklayer.conf", getenv("HOME"));

    FILE *f = fopen(path, "r");
    if (!f) return NULL;

    while (fgets(line, sizeof(line), f)) {
        if (!strncmp(line, "resource=", 9)) {
            char *r = line + 9;
            r[strcspn(r, "\n")] = 0;
            fclose(f);
            return (*r) ? r : NULL;
        }
    }
    fclose(f);
    return NULL;
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_decorated(GTK_WINDOW(win), FALSE);

    gtk_layer_init_for_window(GTK_WINDOW(win));
    gtk_layer_set_layer(GTK_WINDOW(win), GTK_LAYER_SHELL_LAYER_OVERLAY);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_BOTTOM, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(win), GTK_LAYER_SHELL_EDGE_RIGHT, TRUE);

    /* ---------- monitor ---------- */
    GdkRectangle geo = {0};
    if (argc > 1) {
        int id = get_monitor_id(argv[1]);
        if (id >= 0) {
            GdkMonitor *m =
                gdk_display_get_monitor(gdk_display_get_default(), id);
            if (m) {
                gtk_layer_set_monitor(GTK_WINDOW(win), m);
                gdk_monitor_get_geometry(m, &geo);
            }
        }
    }

    if (!geo.width || !geo.height) {
        GdkScreen *s = gdk_screen_get_default();
        geo.width = gdk_screen_get_width(s);
        geo.height = gdk_screen_get_height(s);
    }

    SW = geo.width;
    SH = geo.height;

    GtkWidget *area = gtk_drawing_area_new();
    gtk_widget_set_size_request(area, SW, SH);
    gtk_container_add(GTK_CONTAINER(win), area);

    g_signal_connect(area, "draw", G_CALLBACK(draw_cb), NULL);

    /* ---------- resource load ---------- */
    char *res = get_resource();
    if (res) {
        anim = gdk_pixbuf_animation_new_from_file(res, NULL);
        if (anim)
            iter = gdk_pixbuf_animation_get_iter(anim, NULL);

        if (iter) {
            g_timeout_add(
                gdk_pixbuf_animation_iter_get_delay_time(iter),
                tick_cb,
                area
            );
        }
    }

    gtk_widget_show_all(win);
    gtk_main();
    return 0;
}
