import time
from matplotlib import pyplot as plt
import numpy as np


class LivePlotAnchor:
    def __init__(self, max_anchors, close_event_callback):
        self.plot_hist_length = 100
        self.x = np.linspace(0, self.plot_hist_length)
        self.X, self.Y = np.meshgrid(self.x, self.x)
        self.fig = plt.figure(figsize=(12, 10))
        self.fig.patch.set_facecolor("#65494c")
        self.fig.canvas.manager.set_window_title("Live angles")
        self.fig.subplots_adjust(wspace=0.09)
        self.redraw_counter = 0
        self.max_anchors = max_anchors
        self.close_event_callback = close_event_callback

        # Adjust the padding around all subplots
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.6)
        self.anchors = {}

        self.stats_plt = self.fig.add_subplot(
            self.max_anchors, 2, 2 * self.max_anchors, title="Stats"
        )
        self.stats_plt.set_axis_off()
        self.text_stats = self.stats_plt.text(
            0,
            1,
            "",
            horizontalalignment="left",
            verticalalignment="top",
            color="white",
            size=8,
        )

        self.fig.canvas.draw()  # note that the first draw comes before setting data

        self.stats_pltbackground = self.fig.canvas.copy_from_bbox(self.stats_plt.bbox)

        def closed(event):
            close_event_callback()

        self.fig.canvas.mpl_connect("close_event", closed)

        plt.show(block=False)

    def add_anchor_sample(self, anchor_id, azimuth, elevation):
        if anchor_id not in self.anchors:
            self.anchors[anchor_id] = self.TagGraphData(
                anchor_id,
                self.fig,
                self.plot_hist_length,
                len(self.anchors),
                self.max_anchors,
            )
            self.fig.canvas.draw()
        # Redrawing on every sample will cause delays.
        # This is a bit of a hack to just draw every 5 samples.
        self.redraw_counter = self.redraw_counter + 1
        do_redraw = True if self.redraw_counter % 5 == 0 else False
        self.anchors[anchor_id].add_data(azimuth, elevation, do_redraw)

        if do_redraw and plt.fignum_exists(self.fig.number):
            stats_text = (
                "Anchor\t\t\tMean Azimuth\tMean Elevation\tNum Angles\n".expandtabs()
            )
            stats_text = stats_text + "-" * 100 + "\n"
            for id, tag in self.anchors.items():
                azim_data = tag.get_azimuth_data()
                elev_data = tag.get_elevation_data()
                stats_text = (
                    stats_text
                    + "{}\t{:.2f}\t\t{:.2f}\t\t\t{}\n".format(
                        id,
                        round(np.mean(azim_data), 2),
                        round(np.mean(elev_data), 2),
                        len(azim_data),
                    ).expandtabs()
                )
            self.fig.canvas.restore_region(self.stats_pltbackground),
            self.text_stats.set_text(stats_text)
            self.stats_plt.draw_artist(self.text_stats)
            self.fig.canvas.blit(self.stats_plt.bbox)

    def save_snapshot_png(self, name):
        filename = "{}.png".format(name)
        plt.savefig(filename)
        return filename

    def destroy(self):
        plt.close()

    def set_title(self, title):
        plt.gcf().text(
            0.40,
            0.99,
            title,
            va="top",
            fontsize=14,
        )
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    class TagGraphData:
        def __init__(self, id, fig, max_data_len, index, max_anchors):
            self.id = id
            self.azimuth = []
            self.elevation = []
            self.fig = fig
            self.max_data_len = max_data_len

            self.azim_plt = self.fig.add_subplot(max_anchors, 2, index * 2 + 1)
            self.elev_plt = self.fig.add_subplot(max_anchors, 2, index * 2 + 2)

            self.azim_plt.set_facecolor("#65494c")
            self.azim_plt.tick_params(axis="x", colors="white")
            self.azim_plt.tick_params(axis="y", colors="white")
            self.azim_plt.set_title("Azimuth {0} ".format(id), fontsize=9)

            self.elev_plt.set_facecolor("#65494c")
            self.elev_plt.tick_params(axis="x", colors="white")
            self.elev_plt.tick_params(axis="y", colors="white")
            self.elev_plt.set_title("Elevation {0} ".format(id), fontsize=9)

            (self.azimuth_line,) = self.azim_plt.plot([], lw=2, color="#ffd792")
            (self.elevation_line,) = self.elev_plt.plot([], lw=2, color="#f98941")

            self.azim_plt.set_transform(self.azim_plt.transAxes)
            self.elev_plt.set_transform(self.elev_plt.transAxes)
            self.text_azim = self.azim_plt.text(
                0.01,
                0.95,
                "",
                horizontalalignment="left",
                verticalalignment="top",
                color="white",
                size=11,
                transform=self.azim_plt.transAxes,
            )
            self.text_elev = self.elev_plt.text(
                0.01,
                0.95,
                "",
                horizontalalignment="left",
                verticalalignment="top",
                color="white",
                size=11,
                transform=self.elev_plt.transAxes,
            )

            self.elev_plt.set_xlim(0, self.max_data_len)
            self.elev_plt.set_ylim([-90, 90])

            self.azim_plt.set_xlim(0, self.max_data_len)
            self.azim_plt.set_ylim([-90, 90])

            self.azim_plt.patch.set_edgecolor("black")
            self.azim_plt.patch.set_linewidth("2")
            self.elev_plt.patch.set_edgecolor("black")
            self.elev_plt.patch.set_linewidth("2")
            self.azim_plt.patch.set_color("black")
            self.elev_plt.patch.set_color("black")

            self.azim_plt_background = self.fig.canvas.copy_from_bbox(
                self.azim_plt.bbox
            )
            self.elev_plt_background = self.fig.canvas.copy_from_bbox(
                self.elev_plt.bbox
            )

        def add_data(self, azimuth, elevation, redraw=True):
            # Allow to input multiple data points at once.
            # Otherwise we would have to redraw for each individual sample which is slow.
            if isinstance(azimuth, list):
                print("Is a list")
                self.azimuth = self.azimuth + azimuth
                self.elevation = self.elevation + elevation
                azimuth = 0
                elevation = 0
            else:
                self.azimuth.append(azimuth)
                self.elevation.append(elevation)

            azim_to_plot = self.azimuth[-self.max_data_len :]
            elev_to_plot = self.elevation[-self.max_data_len :]
            self.x = np.linspace(0, len(azim_to_plot), num=len(azim_to_plot))
            self.azimuth_line.set_data(self.x, azim_to_plot)
            self.elevation_line.set_data(self.x, elev_to_plot)
            # restore background
            self.fig.canvas.restore_region(self.azim_plt_background)
            self.fig.canvas.restore_region(self.elev_plt_background)

            self.text_azim.set_text("Angle: {}".format(azimuth))
            self.text_elev.set_text("Angle: {}".format(elevation))

            if redraw and plt.fignum_exists(self.fig.number):
                # redraw just the points
                self.elev_plt.draw_artist(self.elevation_line)
                self.azim_plt.draw_artist(self.azimuth_line)
                self.azim_plt.draw_artist(self.text_azim)
                self.elev_plt.draw_artist(self.text_elev)

                # fill in the axes rectangle
                self.fig.canvas.blit(self.azim_plt.bbox)
                self.fig.canvas.blit(self.elev_plt.bbox)

                # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
                # it is mentionned that blit causes strong memory leakage.
                # however, I did not observe that.

                self.fig.canvas.flush_events()
                # alternatively you could use
                # plt.pause(0.000000000001)
                # however plt.pause calls canvas.draw(), as can be read here:
                # http://bastibe.de/2013-05-30-speeding-up-matplotlib.html

        def get_azimuth_data(self):
            return self.azimuth

        def get_elevation_data(self):
            return self.elevation
