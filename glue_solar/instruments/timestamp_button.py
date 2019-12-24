from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool
import datetime

@viewer_tool
class TimestampButton(CheckableTool):

    icon = 'app_icon'
    tool_id = 'timestamp_button'
    action_text = ''
    tool_tip = 'Activate Timestamp'
    status_tip = 'Timestamp Active'
    shortcut = ''

    def __init__(self, viewer):
        super(TimestampButton, self).__init__(viewer)
        self.activate()

    def activate(self):
        self.viewer.state.add_callback('slices', self.update_label)

    def deactivate(self):
        pass

    def update_label(self, slices):
        data = self.viewer.state.reference_data
        meta = data.meta
        base_time = meta.get("DATE-OBS", meta.get("DATE_OBS", None))

        world = data.coords.pixel2world(*slices[::-1])

        if isinstance(base_time, str):
            timestamp = datetime.datetime.strptime(base_time, '%Y-%m-%dT%H:%M:%S.%f')
        elif isinstance(base_time, datetime.datetime):
            timestamp = base_time
        else:
            return

        if 'CUNIT3' in meta.keys():
            if data.meta['CUNIT3'] == 'seconds':
                timestamp = datetime.timedelta(0, float(world[2])) + timestamp

        elif ('STARTOBS' in meta and 'ENDOBS' in meta):
            date_obs = meta['STARTOBS']
            obs_delt = meta['ENDOBS'] - date_obs
            timestamp = timestamp + obs_delt*float(world[2])

        self.viewer.set_status(timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f'))
