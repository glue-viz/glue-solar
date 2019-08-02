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
        world = data.coords.pixel2world(*slices[::-1])


        if isinstance(data.meta['DATE_OBS'], str):
            date_obs = datetime.datetime.strptime(data.meta['DATE_OBS'], '%Y-%m-%dT%H:%M:%S.%f')
        else:
            date_obs = data.meta['DATE_OBS']
        if 'CUNIT3' in data.meta.keys():
            if data.meta['CUNIT3'] == 'seconds':
                timestamp = datetime.timedelta(0, float(world[2]))+date_obs
        else:
            print(data.__dict__)
            date_obs = data.meta['STARTOBS']
            obs_delt = data.meta['ENDOBS'] - date_obs
            timestamp = date_obs + obs_delt*float(world[2])
        self.viewer.set_status(timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f'))