# This environment is created by Alexander Clegg (alexanderwclegg@gmail.com)

import numpy as np
from gym import utils
from gym.envs.dart.dart_cloth_env import *
import random
import time
import math

from pyPhysX.colors import *
import pyPhysX.pyutils as pyutils
import pyPhysX.renderUtils

import OpenGL.GL as GL
import OpenGL.GLU as GLU
import OpenGL.GLUT as GLUT

class DartClothEndEffectorDisplacerEnv(DartClothEnv, utils.EzPickle):
    def __init__(self):
        self.prefix = os.path.dirname(__file__)
        self.useOpenGL = False
        self.screenSize = (1080, 720)
        self.renderDARTWorld = False
        self.renderUI = True

        #22 dof upper body
        self.action_scale = np.ones(22)*10
        self.control_bounds = np.array([np.ones(22), np.ones(22)*-1])
        
        self.reset_number = 0 #debugging
        self.numSteps = 0

        self.hapticObs = False
        observation_size = 66 #q(sin,cos), dq
        if self.hapticObs:
            observation_size += 66

        model_path = 'UpperBodyCapsules_v3.skel'

        #create cloth scene
        clothScene = pyphysx.ClothScene(step=0.01, sheet=True, sheetW=60, sheetH=15, sheetSpacing=0.025)
        
        #intialize the parent env
        if self.useOpenGL is True:
            DartClothEnv.__init__(self, cloth_scene=clothScene, model_paths=model_path, frame_skip=4,
                                  observation_size=observation_size, action_bounds=self.control_bounds, screen_width=self.screenSize[0], screen_height=self.screenSize[1])
        else:
            DartClothEnv.__init__(self, cloth_scene=clothScene, model_paths=model_path, frame_skip=4,
                                  observation_size=observation_size, action_bounds=self.control_bounds , disableViewer = True, visualize = False)

        utils.EzPickle.__init__(self)
        
        #self.clothScene.seedRandom(random.randint(1,1000))
        self.clothScene.setFriction(0, 0.5)
        
        self.updateClothCollisionStructures(capsules=True, hapticSensors=True)
        
        self.simulateCloth = False

        #enable DART collision testing
        self.robot_skeleton.set_self_collision_check(True)
        self.robot_skeleton.set_adjacent_body_check(False)

        #setup collision filtering
        collision_filter = self.dart_world.create_collision_filter()
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[4],
                                           self.robot_skeleton.bodynodes[6])  # right forearm to upper-arm
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[10],
                                           self.robot_skeleton.bodynodes[12])  # left forearm to upper-arm
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[12],
                                           self.robot_skeleton.bodynodes[14])  # left forearm to fingers
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[6],
                                           self.robot_skeleton.bodynodes[8])  # right forearm to fingers
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[1],
                                           self.robot_skeleton.bodynodes[15])  # torso to neck
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[1],
                                           self.robot_skeleton.bodynodes[16])  # torso to head
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[1],
                                           self.robot_skeleton.bodynodes[3])  # torso to right shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[1],
                                           self.robot_skeleton.bodynodes[9])  # torso to left shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[15],
                                           self.robot_skeleton.bodynodes[3])  # neck to right shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[15],
                                           self.robot_skeleton.bodynodes[9])  # neck to left shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[16],
                                           self.robot_skeleton.bodynodes[3])  # head to right shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[16],
                                           self.robot_skeleton.bodynodes[9])  # head to left shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[3],
                                           self.robot_skeleton.bodynodes[9])  # right shoulder to left shoulder
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[9],
                                           self.robot_skeleton.bodynodes[12])  # left shoulder to left upperarm
        collision_filter.add_to_black_list(self.robot_skeleton.bodynodes[3],
                                           self.robot_skeleton.bodynodes[6])  # right shoulder to right upperarm

        for i in range(len(self.robot_skeleton.bodynodes)):
            print(self.robot_skeleton.bodynodes[i])
            
        for i in range(len(self.robot_skeleton.dofs)):
            print(self.robot_skeleton.dofs[i])
        
    def _step(self, a):
        #print("a: " + str(a))
        clamped_control = np.array(a)
        for i in range(len(clamped_control)):
            if clamped_control[i] > self.control_bounds[0][i]:
                clamped_control[i] = self.control_bounds[0][i]
            if clamped_control[i] < self.control_bounds[1][i]:
                clamped_control[i] = self.control_bounds[1][i]
        tau = np.multiply(clamped_control, self.action_scale)

        fingertip = np.array([0.0, -0.06, 0.0])
        wRFingertip1 = self.robot_skeleton.bodynodes[8].to_world(fingertip)
        wLFingertip1 = self.robot_skeleton.bodynodes[14].to_world(fingertip)
        #vecR1 = self.target-wRFingertip1
        #vecL1 = self.target2-wLFingertip1
        
        #apply action and simulate
        self.do_simulation(tau, self.frame_skip)
        
        wRFingertip2 = self.robot_skeleton.bodynodes[8].to_world(fingertip)
        wLFingertip2 = self.robot_skeleton.bodynodes[14].to_world(fingertip)
        #vecR2 = self.target-wRFingertip2
        #vecL2 = self.target2-wLFingertip2
        
        #force magnitude penalty    
        reward_ctrl = -np.square(tau).sum()

        #reward for maintaining posture
        reward_upright = -abs(self.robot_skeleton.q[0])-abs(self.robot_skeleton.q[1])

        
        #total reward        
        reward = reward_ctrl*0.1 + reward_upright

        ob = self._get_obs()
        s = self.state_vector()
        
        #update physx capsules
        self.updateClothCollisionStructures(hapticSensors=True)
        
        #check cloth deformation for termination
        clothDeformation = 0
        if self.simulateCloth is True:
            clothDeformation = self.clothScene.getMaxDeformationRatio(0)
        
        #check termination conditions
        done = False
        if not np.isfinite(s).all():
            print("Infinite value detected..." + str(s))
            done = True
            reward -= 500
        elif (clothDeformation > 20):
            done = True
            reward -= 500
        #increment the step counter
        self.numSteps += 1
        
        return ob, reward, done, {}

    def _get_obs(self):
        f_size = 66
        '22x3 dofs, 22x3 sensors, 7x2 targets(toggle bit, cartesian, relative)'
        theta = self.robot_skeleton.q
        fingertip = np.array([0.0, -0.06, 0.0])
        #vec = self.robot_skeleton.bodynodes[8].to_world(fingertip) - self.target
        #vec2 = self.robot_skeleton.bodynodes[14].to_world(fingertip) - self.target2

        obs = np.concatenate([np.cos(theta), np.sin(theta), self.robot_skeleton.dq]).ravel()

        if self.hapticObs:
            f = None
            if self.simulateCloth is True:
                f = self.clothScene.getHapticSensorObs()#get force from simulation
            else:
                f = np.zeros(f_size)
            obs = np.concatenate([obs, f]).ravel()

        return obs

    def reset_model(self):
        #print("reset")
        self.cumulativeReward = 0
        self.dart_world.reset()
        self.clothScene.reset()
        self.clothScene.translateCloth(0, np.array([-10.5,0,0]))
        qpos = self.robot_skeleton.q + self.np_random.uniform(low=-.01, high=.01, size=self.robot_skeleton.ndofs)
        qvel = self.robot_skeleton.dq + self.np_random.uniform(low=-.01, high=.01, size=self.robot_skeleton.ndofs)
        self.set_state(qpos, qvel)

        #update physx capsules
        self.updateClothCollisionStructures(hapticSensors=True)
        self.clothScene.clearInterpolation()

        #debugging
        self.reset_number += 1
        self.numSteps = 0

        return self._get_obs()

    def updateClothCollisionStructures(self, capsules=False, hapticSensors=False):
        a=0
        #collision spheres creation
        fingertip = np.array([0.0, -0.06, 0.0])
        z = np.array([0.,0,0])
        cs0 = self.robot_skeleton.bodynodes[1].to_world(z)
        cs1 = self.robot_skeleton.bodynodes[2].to_world(z)
        cs2 = self.robot_skeleton.bodynodes[16].to_world(z)
        cs3 = self.robot_skeleton.bodynodes[16].to_world(np.array([0,0.175,0]))
        cs4 = self.robot_skeleton.bodynodes[4].to_world(z)
        cs5 = self.robot_skeleton.bodynodes[6].to_world(z)
        cs6 = self.robot_skeleton.bodynodes[7].to_world(z)
        cs7 = self.robot_skeleton.bodynodes[8].to_world(z)
        cs8 = self.robot_skeleton.bodynodes[8].to_world(fingertip)
        cs9 = self.robot_skeleton.bodynodes[10].to_world(z)
        cs10 = self.robot_skeleton.bodynodes[12].to_world(z)
        cs11 = self.robot_skeleton.bodynodes[13].to_world(z)
        cs12 = self.robot_skeleton.bodynodes[14].to_world(z)
        cs13 = self.robot_skeleton.bodynodes[14].to_world(fingertip)
        csVars0 = np.array([0.15, -1, -1, 0,0,0])
        csVars1 = np.array([0.07, -1, -1, 0,0,0])
        csVars2 = np.array([0.1, -1, -1, 0,0,0])
        csVars3 = np.array([0.1, -1, -1, 0,0,0])
        csVars4 = np.array([0.065, -1, -1, 0,0,0])
        csVars5 = np.array([0.05, -1, -1, 0,0,0])
        csVars6 = np.array([0.0365, -1, -1, 0,0,0])
        csVars7 = np.array([0.04, -1, -1, 0,0,0])
        csVars8 = np.array([0.036, -1, -1, 0,0,0])
        csVars9 = np.array([0.065, -1, -1, 0,0,0])
        csVars10 = np.array([0.05, -1, -1, 0,0,0])
        csVars11 = np.array([0.0365, -1, -1, 0,0,0])
        csVars12 = np.array([0.04, -1, -1, 0,0,0])
        csVars13 = np.array([0.036, -1, -1, 0,0,0])
        collisionSpheresInfo = np.concatenate([cs0, csVars0, cs1, csVars1, cs2, csVars2, cs3, csVars3, cs4, csVars4, cs5, csVars5, cs6, csVars6, cs7, csVars7, cs8, csVars8, cs9, csVars9, cs10, csVars10, cs11, csVars11, cs12, csVars12, cs13, csVars13]).ravel()
        #collisionSpheresInfo = np.concatenate([cs0, csVars0, cs1, csVars1]).ravel()
        
        self.clothScene.setCollisionSpheresInfo(collisionSpheresInfo)
        
        if capsules is True:
            #collision capsules creation
            collisionCapsuleInfo = np.zeros((14,14))
            collisionCapsuleInfo[0,1] = 1
            collisionCapsuleInfo[1,2] = 1
            collisionCapsuleInfo[1,4] = 1
            collisionCapsuleInfo[1,9] = 1
            collisionCapsuleInfo[2,3] = 1
            collisionCapsuleInfo[4,5] = 1
            collisionCapsuleInfo[5,6] = 1
            collisionCapsuleInfo[6,7] = 1
            collisionCapsuleInfo[7,8] = 1
            collisionCapsuleInfo[9,10] = 1
            collisionCapsuleInfo[10,11] = 1
            collisionCapsuleInfo[11,12] = 1
            collisionCapsuleInfo[12,13] = 1
            self.clothScene.setCollisionCapsuleInfo(collisionCapsuleInfo)
            
        if hapticSensors is True:
            #hapticSensorLocations = np.concatenate([cs0, LERP(cs0, cs1, 0.33), LERP(cs0, cs1, 0.66), cs1, LERP(cs1, cs2, 0.33), LERP(cs1, cs2, 0.66), cs2, LERP(cs2, cs3, 0.33), LERP(cs2, cs3, 0.66), cs3])
            #hapticSensorLocations = np.concatenate([cs0, LERP(cs0, cs1, 0.25), LERP(cs0, cs1, 0.5), LERP(cs0, cs1, 0.75), cs1, LERP(cs1, cs2, 0.25), LERP(cs1, cs2, 0.5), LERP(cs1, cs2, 0.75), cs2, LERP(cs2, cs3, 0.25), LERP(cs2, cs3, 0.5), LERP(cs2, cs3, 0.75), cs3])
            hapticSensorLocations = np.concatenate([cs0, cs1, cs2, cs3, cs4, LERP(cs4, cs5, 0.33), LERP(cs4, cs5, 0.66), cs5, LERP(cs5, cs6, 0.33), LERP(cs5,cs6,0.66), cs6, cs7, cs8, cs9, LERP(cs9, cs10, 0.33), LERP(cs9, cs10, 0.66), cs10, LERP(cs10, cs11, 0.33), LERP(cs10, cs11, 0.66), cs11, cs12, cs13])
            self.clothScene.setHapticSensorLocations(hapticSensorLocations)
            
    def getViewer(self, sim, title=None, extraRenderFunc=None, inputFunc=None):
        return DartClothEnv.getViewer(self, sim, title, self.extraRenderFunction, self.inputFunc)

    def inputFunc(self, repeat=False):
        pyutils.inputGenie(domain=self, repeat=repeat)

    def extraRenderFunction(self):
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3d(0,0,0)
        GL.glVertex3d(-1,0,0)
        GL.glEnd()

        if self.renderUI:
            self.clothScene.drawText(x=15., y=30., text="Steps = " + str(self.numSteps), color=(0., 0, 0))
            if self.numSteps > 0:
                renderUtils.renderDofs(robot=self.robot_skeleton, restPose=None, renderRestPose=False)

    def viewer_setup(self):
        if self._get_viewer().scene is not None:
            self._get_viewer().scene.tb.trans[2] = -3.5
            self._get_viewer().scene.tb._set_theta(180)
            self._get_viewer().scene.tb._set_phi(180)
        self.track_skeleton_id = 0
        if not self.renderDARTWorld:
            self.viewer.renderWorld = False
        self.clothScene.renderCollisionCaps = True
        self.clothScene.renderCollisionSpheres = True

def LERP(p0, p1, t):
    return p0 + (p1-p0)*t