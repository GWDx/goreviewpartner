# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from katagtp import katagtp
import sys
from time import sleep
from Tkinter import *
from toolbox import *
from toolbox import _
from time import time

class KataAnalysis():

	def run_analysis(self,current_move):
		
		one_move=go_to_move(self.move_zero,current_move)
		player_color=guess_color_to_play(self.move_zero,current_move)
		Kata=self.Kata
		
		log()
		log("==============")
		log("move",current_move)
		
        ##KATAGO.EXE
		#additional_comments=""
		Kata.komiset()
		if player_color in ('w',"W"):
			log("Kata play white")
			Kata.analyze_white()
		else:
			log("Kata play black")
			Kata.analyze_black()

		if current_move>1:
			es=Kata.final_score()
			node_set(one_move,"ES",es)
		
		position_evaluation=Kata.get_all_Kata_moves()
		
		answer=position_evaluation['move']
		Kata.appendAns(player_color,answer)
		
		if (answer in ["PASS","RESIGN"]):
			Kata.undo()
		else:
			#let's make sure there is at least one variation available
			# if len(position_evaluation['variations'])==0:
			# 	position_evaluation['variations'].append({'sequence':answer})
			
			nb_undos=1 #let's remember to undo that move from Leela Zero

			#let's make sure that there is more than one move for the first line of play
			#only one move could be a bookmove, or a very very forcing move
			first_sequence=position_evaluation['variations'][0]['sequence']
			new_sequence=first_sequence
			"""
			while len(new_sequence.split())<=1 and nb_undos<=5:
				log("first, let's ask Katago for the next move")
				if player_color in ('w',"W") and nb_undos%2==0:
					answer=Kata.play_white()
				elif player_color in ('w',"W") and nb_undos%2==1:
					answer=Kata.play_black()
				elif player_color not in ('w',"W") and nb_undos%2==0:
					answer=Kata.play_black()
				else:
					answer=Kata.play_white()
				nb_undos+=1 #one have to remember to undo that move later
				
				new_position_evaluation=Kata.get_all_Kata_moves() #let's get stats for this new move
				
				#let's make sure there is at least one variation available
				if len(new_position_evaluation['variations'])==0:
					new_position_evaluation['variations'].append({'sequence':answer})
				
				# if (answer not in ["PASS","RESIGN"]):
				# 	#let's check the lenght of the new sequence
				# 	new_sequence=new_position_evaluation["variations"][0]["sequence"]
				# 	#adding this new sequence to the old sequence
				# 	position_evaluation['variations'][0]['sequence']+=" "+new_sequence

				else:
					#Katago does not want to play further on this line of play
					#so let's stop there
					break
			"""
			for u in range(nb_undos):
				#log("undo...")
				Kata.undo()
			
		log(len(answer),"sequences")
		best_answer=answer
		node_set(one_move,"CBM",answer) #Computer Best Move

		
		best_move=True
		log("Number of alternative sequences:",len(position_evaluation['variations']))
		for variation in position_evaluation['variations'][:self.maxvariations]:
			#exemple: {'value network win rate': '50.22%', 'policy network value': '17.37%', 'sequence': 'Q16 D4 D17 Q4', 'playouts': '13', 'first move': 'Q16'}
			previous_move=one_move.parent
			current_color=player_color	
			first_variation_move=True
			for one_deep_move in variation['sequence'].split(' ')[:-1]:
				if one_deep_move in ["PASS","RESIGN"]:
					log("Leaving the variation when encountering",one_deep_move)
					break

				i,j=gtp2ij(one_deep_move)
				new_child=previous_move.new_child()
				node_set(new_child,current_color,(i,j))
				
				if first_variation_move==True:
					first_variation_move=False
					#variation_comment=""
		
					if 'win rate' in variation:
						if player_color=='b':
							black_value=variation['win rate']
							white_value=opposite_rate(black_value)
						else:
							white_value=variation['win rate']
							black_value=opposite_rate(white_value)	
						node_set(new_child,"VNWR",black_value+'/'+white_value)
						if best_move:
							node_set(one_move,"VNWR",black_value+'/'+white_value)

					if 'score' in variation:
						node_set(new_child,"ES",variation['score'])

					if 'playouts' in variation:
						node_set(new_child,"PLYO",variation['playouts'])
					
					#new_child.add_comment_text(variation_comment)
					
					if best_move:
						best_move=False
					
				previous_move=new_child
				if current_color in ('w','W'):
					current_color='b'
				else:
					current_color='w'
		log("==== no more sequences =====")
		
		try:
			max_reading_depth=position_evaluation['max reading depth']
			node_set(one_move,"MRD",str(max_reading_depth))
			average_reading_depth=position_evaluation['average reading depth']
			node_set(one_move,"ARD",str(average_reading_depth))
		except:
			pass
        
		return best_answer
	
	def initialize_bot(self):
		Kata=Kata_starting_procedure(self.g,self.profile)
		self.Kata=Kata
		self.time_per_move=0
		return Kata

def Kata_starting_procedure(sgf_g,profile,silentfail=False):
	return bot_starting_procedure("Kata","KataGo",Kata_gtp,sgf_g,profile,silentfail)


class RunAnalysis(KataAnalysis,RunAnalysisBase):
	def __init__(self,parent,filename,move_range,intervals,variation,komi,profile,existing_variations="remove_everything"):
		RunAnalysisBase.__init__(self,parent,filename,move_range,intervals,variation,komi,profile,existing_variations)

class LiveAnalysis(KataAnalysis,LiveAnalysisBase):
	def __init__(self,g,filename,profile):
		LiveAnalysisBase.__init__(self,g,filename,profile)

import ntpath
import subprocess
import Queue

class Position(dict):
	def __init__(self):
		self['variations']=[]

class Variation(dict):
	pass

class Kata_gtp(katagtp):

	def __init__(self,command):
		self.c=1
		self.command_line=command[0]+" "+" ".join(command[1:])
		command=[c.encode(sys.getfilesystemencoding()) for c in command]
		self.process=subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		self.size=0
		
		self.stderr_starting_queue=Queue.Queue(maxsize=100)
		self.stderr_queue=Queue.Queue()
		self.stdout_queue=Queue.Queue()
		threading.Thread(target=self.consume_stderr).start()
		
		log("Checking Kata stderr to check for OpenCL SGEMM tuner running")
		delay=60
		while 1:
			try:
				err_line=self.stderr_starting_queue.get(True,delay)
				delay=10
				if "Started OpenCL SGEMM tuner." in err_line:
					log("OpenCL SGEMM tuner is running")
					show_info(_("Kata is currently running the OpenCL SGEMM tuner. It may take several minutes until Kata is ready."))
					break
				elif "Loaded existing SGEMM tuning.\n" in err_line:
					log("OpenCL SGEMM tuner has already been runned")
					break
				elif "BLAS Core:" in err_line:
					log("Could not find out, abandoning")
					break
				elif "Could not open weights file" in err_line:
					show_info(err_line.strip())
					break
				elif "Weights file is the wrong version." in err_line:
					show_info(err_line.strip())
					break

			except:
				log("Could not find out, abandoning")
				break
		
		
		self.free_handicap_stones=[]
		self.history=[]

	def consume_stderr(self):
		while 1:
			try:
				err_line=self.process.stderr.readline()
				if err_line:
					self.stderr_queue.put(err_line)
					try:
						self.stderr_starting_queue.put(err_line,block=False)
					except:
						#no need to keep all those log in memory, so there is a limit at 100 lines
						pass
				else:
					log("leaving consume_stderr thread")
					return
			except Exception, e:
				log("leaving consume_stderr thread due to exception:")
				log(e)
				return

	def quick_evaluation(self,color):
		
		if color==2:
			answer=self.play_white()
		else:
			answer=self.play_black()
		
		unused,unused,unused,unused,unused,win,unused=answer[0]
		
		txt=""
		if win:
			if color==1:
				winrate=str(float(win))+'%/'+str(100-float(win))+'%'
			else:
				winrate=str(100-float(win))+'%/'+str(win)+'%'
			txt+= variation_data_formating["BWWR"]%winrate

		return txt
	
	def get_Kata_final_score(self):
		self.write("final_score")
		answer=self.readline().strip()
		try:
			return answer.split(" ")[1]
		except:
			raise GRPException("GRPException in Get_Kata_final_score()")


	def get_all_Kata_moves(self):
		# buff=[]
		
		line=self.readline()
		if line=="= \r\n":
			line=self.readline()
		if line=="=\r\n":
			line=self.readline()
		move=(self.readline().split(" ")[-1])[:-2]
		buff=line.split("info move")
		# while not self.stdout_queue.empty():
		# 	while not self.stdout_queue.empty():
		# 		buff.append(self.stdout_queue.get())
		# 	sleep(.1)
		
		buff.reverse()
		
		position_evaluation=Position()
		
		for err_line in buff:
			#log(err_line)
			try: #for comptability with Leela Zero dynamic komi
				# if "average depth," in err_line and "max depth" in err_line:
				# 	position_evaluation["average reading depth"]=float(err_line.split()[0])
				# 	position_evaluation["max reading depth"]=int(err_line.split()[3])
				# if " ->" in err_line:
				if " " in err_line:
					if err_line[0]==" ":
						#log(err_line)
						variation=Variation()
						
						one_answer=err_line.strip().split(" ")[0]
						variation["first move"]=one_answer
						
						nodes=err_line.strip().split("visits ")[1].split(" ")[0]
						variation["playouts"]=nodes
						
						temp=err_line.split("winrate ")[1].split(' ')[0].strip()
						winrate=temp[2:4]+"."+temp[5:]+"%"
						variation["win rate"]=winrate #for Leela Zero, the value network is used as win rate
						
						score=err_line.split("scoreMean ")[1].split(' ')[0].strip()
						variation["score"]=score
						
						# prior lcb order

						sequence=err_line.split("pv ")[1]
						variation["sequence"]=sequence.upper()

						#answers=[[one_answer,sequence,value_network,policy_network,nodes]]+answers
						position_evaluation['variations']=[variation]+position_evaluation['variations']
			except:
				pass

			position_evaluation['move']=move

		return position_evaluation


class KataSettings(BotProfiles):
	def __init__(self,parent,bot="Kata"):
		BotProfiles.__init__(self,parent,bot)
		self.bot_gtp=Kata_gtp


class KataOpenMove(BotOpenMove):
	def __init__(self,sgf_g,profile):
		BotOpenMove.__init__(self,sgf_g,profile)
		self.name='Kata'
		self.my_starting_procedure=Kata_starting_procedure


Kata={}
Kata['name']="Kata"
Kata['gtp_name']="KataGo"
Kata['analysis']=KataAnalysis
Kata['openmove']=KataOpenMove
Kata['settings']=KataSettings
Kata['gtp']=Kata_gtp
Kata['liveanalysis']=LiveAnalysis
Kata['runanalysis']=RunAnalysis
Kata['starting']=Kata_starting_procedure

if __name__ == "__main__":
	main(Kata)
