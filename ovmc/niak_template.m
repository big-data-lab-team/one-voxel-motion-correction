files_in = {};
files_in.subject.run = '[DATASET]';
opt = {};
opt.folder_out = '[FOLDER_OUT]';
niak_pipeline_motion[CHAINED](files_in, opt);

transfos = load('[FOLDER_OUT]/motion_parameters_subject_subject_run.mat');
param = zeros(length([N_VOLS]),6);
# Copied from SPM brick
for i=1:[N_VOLS]
    [rot,tsl] = niak_transf2param(transfos.transf(:,:,i));
    param(i,:) = [tsl' rot(3) rot(1) rot(2)];
end
save('[OUTPUT_FILE]','-ascii','param');
