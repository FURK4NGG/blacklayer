#include <gtk/gtk.h>
#include <gtk-layer-shell.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* -------------------------------------------------
 * Hyprland monitor name -> ID
 * ------------------------------------------------- */
static int get_monitor_id(const char *name) {
    char cmd[512];
    snprintf(
        cmd,
        sizeof(cmd),
        "hyprctl -j monitors | jq -r '.[] | select(.name==\"%s\") | .id'",
        name
    );

    FILE *fp = popen(cmd, "r");
    if (!fp)
        return -1;

    int id = -1;
    fscanf(fp, "%d", &id);
    pclose(fp);

    return id;
}

/* -------------------------------------------------
 * Read resource from blacklayer.conf
 * ------------------------------------------------- */
static char *get_resource_path(void) {
    const char *home = getenv("HOME");
    if (!home)
        return NULL;

    char path[512];
    snprintf(path, sizeof(path),
             "%s/.config/blacklayer/blacklayer.conf", home);

    FILE *fp = fopen(path, "r");
    if (!fp)
        return NULL;

    static char line[1024];
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "resource=", 9) == 0) {
            char *res = line + 9;
            res[strcspn(res, "\n")] = 0;
            fclose(fp);
            return (*res) ? res : NULL;
        }
    }

    fclose(fp);
    return NULL;
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_decorated(GTK_WINDOW(window), FALSE);
    gtk_window_set_resizable(GTK_WINDOW(window), FALSE);

    gtk_layer_init_for_window(GTK_WINDOW(window));
    gtk_layer_set_layer(GTK_WINDOW(window),
                        GTK_LAYER_SHELL_LAYER_OVERLAY);

    gtk_layer_set_anchor(GTK_WINDOW(window),
                         GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window),
                         GTK_LAYER_SHELL_EDGE_BOTTOM, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window),
                         GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window),
                         GTK_LAYER_SHELL_EDGE_RIGHT, TRUE);

    /* Monitor selection */
    if (argc > 1) {
        int id = get_monitor_id(argv[1]);
        if (id >= 0) {
            GdkDisplay *display = gdk_display_get_default();
            GdkMonitor *monitor =
                gdk_display_get_monitor(display, id);
            if (monitor)
                gtk_layer_set_monitor(GTK_WINDOW(window), monitor);
        }
    }

    GtkWidget *overlay = gtk_overlay_new();
    gtk_container_add(GTK_CONTAINER(window), overlay);

    char *resource = get_resource_path();

    if (resource) {
        GtkWidget *image = gtk_image_new_from_file(resource);
        gtk_widget_set_hexpand(image, TRUE);
        gtk_widget_set_vexpand(image, TRUE);
        gtk_overlay_add_overlay(GTK_OVERLAY(overlay), image);
    } else {
        GtkCssProvider *css = gtk_css_provider_new();
        gtk_css_provider_load_from_data(
            css,
            "window { background-color: black; }",
            -1,
            NULL
        );

        gtk_style_context_add_provider_for_screen(
            gdk_screen_get_default(),
            GTK_STYLE_PROVIDER(css),
            GTK_STYLE_PROVIDER_PRIORITY_APPLICATION
        );
    }

    gtk_widget_show_all(window);
    gtk_main();
    return 0;
}
