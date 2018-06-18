files_in = {}
files_in.subject.run = '[DATASET]'
opt = {}
opt.folder_out = '[FOLDER_OUT]'
  niak_pipeline_motion(files_in, opt)

transfos = load('[FOLDER_OUT]/motion_parameters_subject_subject_run.mat')
for i=1:[N_VOLS]
	niak_write_transf(transfos.transf(:,:,i), strcat('[FOLDER_OUT]/transf_',int2str(i),'.xfm'))
end
