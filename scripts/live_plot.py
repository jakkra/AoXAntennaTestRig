import time
from matplotlib import pyplot as plt
import numpy as np


class LivePlot:
    def __init__(self, figsize, antenna_azimuth, antenna_tilt):
        self.plot_hist_length = 100
        plt.rcParams.update({"text.color": "white"})
        self.x = np.linspace(0, self.plot_hist_length)
        self.X, self.Y = np.meshgrid(self.x, self.x)
        self.fig = plt.figure(figsize=figsize)
        self.fig.patch.set_facecolor("#65494c")
        self.fig.subplots_adjust(wspace=0.09)
        plt.gcf().text(
            0.40,
            0.99,
            "Ground truth ({}, {})".format(antenna_azimuth, antenna_tilt),
            va="top",
            fontsize=18,
        )
        # Adjust the padding around all subplots
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.4)
        self.tags = {}

        self.stats_plt = self.fig.add_subplot(6, 2, 12, title="Stats")
        self.stats_plt.set_axis_off()
        self.text_stats = self.stats_plt.text(
            0,
            1,
            "",
            horizontalalignment="left",
            verticalalignment="top",
            color="white",
            size=10,
        )

        self.fig.canvas.draw()  # note that the first draw comes before setting data

        self.stats_pltbackground = self.fig.canvas.copy_from_bbox(self.stats_plt.bbox)
        plt.show(block=False)

    def add_tag_sample(self, tag_id, azimuth, elevation, azimith_gt, elevation_gt):
        if tag_id not in self.tags:
            self.tags[tag_id] = self.TagGraphData(
                tag_id,
                self.fig,
                self.plot_hist_length,
                len(self.tags),
                azimith_gt,
                elevation_gt,
            )
            self.fig.canvas.draw()

        self.tags[tag_id].add_data(azimuth, elevation)

        stats_text = "TAG\t\t\tMean Azimuth (err)\tMean Elevation (err)\tNum Angles\n".expandtabs()
        stats_text = stats_text + "-" * 100 + "\n"
        for id, tag in self.tags.items():
            azim_data = tag.get_azimuth_data()
            elev_data = tag.get_elevation_data()
            stats_text = (
                stats_text
                + "{}\t{:.2f}({:.2f})\t\t{:.2f}({:.2f})\t\t\t{}\n".format(
                    id,
                    round(np.mean(azim_data), 2),
                    round(abs(np.mean(azim_data) - azimith_gt), 2),
                    round(np.mean(elev_data), 2),
                    round(abs(np.mean(elev_data) - elevation_gt), 2),
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

    class TagGraphData:
        def __init__(self, id, fig, max_data_len, index, azimith_gt, elevation_gt):
            self.id = id
            self.azimuth = []
            self.elevation = []
            self.azimith_gt = azimith_gt
            self.elevation_gt = elevation_gt
            self.fig = fig
            self.max_data_len = max_data_len

            print("Add tag to plot")
            self.azim_plt = self.fig.add_subplot(
                6, 2, index * 2 + 1, title="Azimuth {0} ".format(id)
            )
            self.elev_plt = self.fig.add_subplot(
                6, 2, index * 2 + 2, title="Elevation {0} ".format(id)
            )

            self.azim_plt.set_facecolor("#65494c")
            self.azim_plt.tick_params(axis="x", colors="white")
            self.azim_plt.tick_params(axis="y", colors="white")

            self.elev_plt.set_facecolor("#65494c")
            self.elev_plt.tick_params(axis="x", colors="white")
            self.elev_plt.tick_params(axis="y", colors="white")

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

            self.azim_gt_line = self.azim_plt.hlines(
                y=self.azimith_gt,
                xmin=0,
                xmax=self.max_data_len,
                linewidth=0.5,
                color="#99ff66",
            )
            self.elev_gt_line = self.elev_plt.hlines(
                y=self.elevation_gt,
                xmin=0,
                xmax=self.max_data_len,
                linewidth=0.5,
                color="#99ff66",
            )

            self.azim_plt_background = self.fig.canvas.copy_from_bbox(
                self.azim_plt.bbox
            )
            self.elev_plt_background = self.fig.canvas.copy_from_bbox(
                self.elev_plt.bbox
            )

        def add_data(self, azimuth, elevation):
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

            self.text_azim.set_text(
                "{} => err: {}".format(azimuth, abs(self.azimith_gt - azimuth))
            )
            self.text_elev.set_text(
                "{} => err: {}".format(elevation, abs(self.elevation_gt - elevation))
            )

            # redraw just the points
            self.elev_plt.draw_artist(self.elevation_line)
            self.azim_plt.draw_artist(self.azimuth_line)
            self.azim_plt.draw_artist(self.text_azim)
            self.elev_plt.draw_artist(self.text_elev)
            self.azim_plt.draw_artist(self.azim_gt_line)
            self.elev_plt.draw_artist(self.elev_gt_line)

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
