import cv2
import sys
from darkflow.net.build import TFNet
import time
import operator
check_value = 5
no_of_trackers = 2
IOU_THRESHOLD = .7

if sys.platform == 'win32':
    print ('Setting windows options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3
    }
else:
    print('Setting unix options')
    options = {
        'model': 'cfg/yolo.cfg',
        'load': 'bin/yolov2.weights',
        'threshold': 0.3,
        'gpu' : 1
    }

labels = ['person','tvmonitor']
colors = {'person':(0,0,0),'tvmonitor':(0,0,255)}

tfnet = TFNet(options)

class Trackers:

    def __init__(self,frame,bbox):
        # Initialize bboxes if you want to preset tracking
        self.trackers = {}
        self.ids = 0
        new_labels = False
        if bbox != None:
            for i in range(0, len(bbox)):
                tracker = self.create_tracker()
                ok = tracker.init(frame, bbox[i]['bbox'])
                id1 = bbox[i]['id']
                if ok == True: self.trackers[id1] = ({'status': ok, 'tracker': tracker, 'bbox': bbox[i]['bbox']})
        else:
            # allow for new targets if new labels
            new_labels = True
            Newbboxes = self.get_bound_boxes(frame)
            for i in range(0, len(Newbboxes)):
                tracker = self.create_tracker()
                ok = tracker.init(frame, Newbboxes[i][2])
                id1 = self.ids
                self.ids = self.ids + 1
                if ok == True: self.trackers[id1] = ({'status': ok, 'tracker': tracker, 'bbox': Newbboxes[i][2]})


        return self.trackers


    def create_tracker(self):
        tracker_types = ['BOOSTING', 'MIL', 'KCF', 'TLD', 'MEDIANFLOW' ]
        # No 2 = KCF is best
        tracker_type = tracker_types[2]
        if tracker_type == 'BOOSTING':
            return cv2.TrackerBoosting_create()
        if tracker_type == 'MIL':
            return cv2.TrackerMIL_create()
        if tracker_type == 'KCF':
            return cv2.TrackerKCF_create()
        if tracker_type == 'TLD':
            return cv2.TrackerTLD_create()
        if tracker_type == 'MEDIANFLOW':
            return cv2.TrackerMedianFlow_create()

    def assign_tracker(self,bboxes,key,frame):
        tracker = self.create_tracker()
        new_tracker = {}
        # convert p2 into ROI format
        p2 = bboxes[key][2]
        ok = tracker.init(frame, p2)
        new_tracker['status'] = ok
        new_tracker['tracker'] = tracker
        new_tracker['bbox'] = p2
        new_tracker['brox'] = ((bboxes[key][1][0], bboxes[key][1][1]), (bboxes[key][1][2], bboxes[key][1][3]))
        return new_tracker

    def get_bound_boxes(self,frame):
        # TODO carrying over id and adding new ids

        results = tfnet.return_predict(frame)
        bboxes = []
        i = 0
        for result in  results:
            label = result['label']
            if label in labels :
                # only certain labels put bound boxes
                arr1 = (int(result['topleft']['x']), int(result['topleft']['y']),
                                int(result['bottomright']['x']), int(result['bottomright']['y']))
                # IOU format
                arr2 = (int(result['topleft']['x']), int(result['topleft']['y']),
                 int(result['bottomright']['x']) - int(result['topleft']['x']),
                 int(result['bottomright']['y']) - int(result['topleft']['y']))
                bboxes.append ((i,arr1,arr2))
                i = i + 1
                # format for tracking
                # p1 = (int(bbox[0]), int(bbox[1]))
                # p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))

        return bboxes

    def get_iou(self,bb1, bb2):
        """
        Calculate the Intersection over Union (IoU) of two bounding boxes.

        Parameters
        ----------
        bb1 : list
            The (x1, y1) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner
        bb2 : list
            The (x, y) position is at the top left corner,
            the (x2, y2) position is at the bottom right corner

        Returns
        -------
        float
            in [0, 1]
        """

        # determine the coordinates of the intersection rectangle
        x_left = max(bb1[0], bb2[0])
        y_top = min(bb1[1], bb2[1])
        x_right = min(bb1[2], bb2[2])
        y_bottom = max(bb1[3], bb2[3])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        # The intersection of two axis-aligned bounding boxes is always an
        # axis-aligned bounding box
        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # compute the area of both AABBs
        bb1_area = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
        bb2_area = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])

        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
        # assert iou >= 0.0
        # assert iou <= 1.0
        return iou

    def get_closest_match(self, bboxes, frame):
        # Note this gets the CLOSEST matches!!!!
        tracker_array = {}
        assigned_bboxes = {}
        for i in self.trackers.keys():
            # do this for only valid trackers!
            if self.trackers[i]['status'] == True:
                tracker_array[i] = i
                # initialize bboxes and IOU dictionary
                tracker_array[i] = {}
                bbox = self.trackers[i]['bbox']
                # convert into TL, BR format
                p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                for y in range(0, len(bboxes)):
                    p2 = bboxes[y][1]
                    iou = self.get_iou((p1), (p2))
                    tracker_array[i].update({y,iou})

                # get the highest tracker above IOU_Threshold
                stats = tracker_array[i]
                key = max(stats.items(), key=operator.itemgetter(1))[0]
                if stats[key] > IOU_THRESHOLD:
                    if key in assigned_bboxes:
                        print('BBox already assigned')
                        print('Assigning anyway!!!')
                    else:
                        assigned_bboxes[key] = key
                    # assigned correct bbox values to tracker
                    self.trackers[i] = self.assign_tracker(bboxes, key, frame)
                else:
                    # invalidate tracker
                    self.trackers[i]['status'] = False

        # get bboxes not assigned and assign to new tracker
        # check status before assigning
        bbox_key_values = [item[0] for item in bboxes]
        unassigned_bbox_key_values = [i for i in bbox_key_values if i not in assigned_bboxes]
        for i in unassigned_bbox_key_values:
            print('assigning new trackers')
            tracker = self.create_tracker()
            ok = tracker.init(frame, bboxes[i][2])
            id1 = self.ids
            self.ids = self.ids + 1
            if ok == True: self.trackers[id1] = ({'status': ok, 'tracker': tracker, 'bbox': bboxes[i][2]})

    def get_match(self, bboxes, frame):
        # find matches for existing trackers including clearing out invalid trackers
        # go through all valid trackers and find their equivalent bound box
        # if there is no match for a tracker invalidate it!
        # Note this does not get the closest matches!!!!
        for i in self.trackers.keys():
            # do this for only valid trackers!
            if self.trackers[i]['status'] == True:
                found = False
                bbox = self.trackers[i]['bbox']
                # convert into TL, BR format
                p1 = (int(bbox[0]), int(bbox[1]), int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                for y in range(0, len(bboxes)):
                    p2 = bboxes[y][1]
                    iou = self.get_iou((p1), (p2))

                    if iou > IOU_THRESHOLD:
                        print('iou', iou)
                        found = True
                        # update tracker
                        self.trackers[i] = self.assign_tracker(bboxes, y, frame)
                        break

                if found == False:
                    self.trackers[i]['status'] = False



    def retarget(self,frame):
        Newbboxes = self.get_bound_boxes(frame)
        if self.new_labels == True:
            self.get_closest_match(Newbboxes, frame)
        else:
            self.get_match(Newbboxes, frame)

    def update_trackers(self,frame):
        # Update all trackers
        for i in self.trackers.keys():
            if self.trackers[i]['status'] == True:
            # retrieve trackers for each bound box
                tracker = self.trackers[i]['tracker']
                ok, bbox1 = tracker.update(frame)
                self.trackers[i]['status'] = ok
                self.trackers[i]['bbox'] = bbox1


def testHarness():

    # Define an initial bounding box
    bbox = []
    # bbox values provided by selectROI
    #bbox = cv2.selectROI(frame, False)
    # ROI Format. Need to change BR co-ordinates!!!!
    bbox.append({'id':0,'bbox':(81, 93, 91, 234)})
    bbox.append({'id':6,'bbox':(354, 77, 74, 257)})
    # Set up trackers for number of bounding boxes.
    # Instead of MIL, you can also use
    # bbox values provided by TF x,y , manipulated x , manipulated y
    #bbox.append((91, 97, 65, 225))
    #bbox.append((352, 70, 83, 272))


    # Read video
    video = cv2.VideoCapture("./video/TUD-Stadtmitte.mp4")

    if not video.isOpened():
        print("Could not open video")
        sys.exit()

    # Read first frame.
    ok, frame = video.read()
    if not ok:
        print('Cannot read video file')
        sys.exit()

    # initialize trackers for all labels on the initial frame
    mytracker = Trackers(frame)
    counter = 0
    while True:
        # Read 2nd frame onwards
        ok, frame = video.read()
        if not ok:
            break

        if counter % check_value == 0 and counter !=0:
            # every nth course correct
            # and reset tracker - set new bbox
            print('reTargetting', counter)
            mytracker.retarget(frame)
        else:
            mytracker.update(frame)